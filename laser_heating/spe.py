"""SPE 3.0 helpers for direct acquisition.

The PICAM driver knows nothing about the spectrograph, so a LightField SPE
taken at the same grating position supplies the wavelength axis and the sensor
regions that are read out. Captures are written back as SPE 3.0 so the
existing reader, LightField and T-Rax can open them.
"""
from dataclasses import dataclass
from pathlib import Path
import time
from xml.etree import ElementTree
from xml.sax.saxutils import quoteattr

import numpy as np

HEADER_BYTES = 4100
SPE_NAMESPACE = "http://www.princetoninstruments.com/spe/2009"
EXPERIMENT_NAMESPACE = "http://www.princetoninstruments.com/experiment/2009"


@dataclass(frozen=True)
class SensorRegion:
    """Sensor pixels read for one band of the saved image (LightField convention)."""

    x: int
    width: int
    x_binning: int
    y: int
    height: int
    y_binning: int

    def __post_init__(self) -> None:
        values = (self.x, self.width, self.x_binning, self.y, self.height, self.y_binning)
        if any(type(value) is not int for value in values):
            raise ValueError("Sensor region values must be integers")
        if min(self.x, self.y) < 0 or min(self.width, self.height, self.x_binning, self.y_binning) <= 0:
            raise ValueError("Sensor region is outside the sensor")
        if self.width % self.x_binning or self.height % self.y_binning:
            raise ValueError("Sensor region size must be a multiple of its binning")

    @property
    def columns(self) -> int:
        return self.width // self.x_binning

    @property
    def rows(self) -> int:
        return self.height // self.y_binning


@dataclass(frozen=True)
class CameraSetup:
    """Camera settings found in an SPE footer or a LightField .lfe file."""

    exposure_seconds: float | None = None
    regions: tuple[SensorRegion, ...] = ()
    adc_speed_mhz: float | None = None
    adc_analog_gain: str | None = None
    adc_quality: str | None = None


@dataclass(frozen=True)
class SpeReference:
    source: Path
    sensor_width: int
    sensor_height: int
    sensor_wavelengths_nm: np.ndarray  # one per unbinned sensor column
    setup: CameraSetup

    def wavelengths_for(self, regions) -> np.ndarray:
        return region_wavelengths(self.sensor_wavelengths_nm, regions)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find(element, *names):
    """First descendant path by local tag names, ignoring XML namespaces."""
    for name in names:
        if element is None:
            return None
        element = next((child for child in element.iter() if child is not element and _local(child.tag) == name), None)
    return element


def _text(element, *names):
    found = _find(element, *names)
    return found.text.strip() if found is not None and found.text and found.text.strip() else None


def _region(element) -> SensorRegion:
    get = lambda name, default=None: int(element.attrib.get(name, default))
    return SensorRegion(get("x"), get("width"), get("xBinning", 1), get("y"), get("height"), get("yBinning", 1))


def camera_setup_from_xml(root, sensor_size=None) -> CameraSetup:
    """Read the settings the PICAM driver understands; anything else is ignored."""
    camera = None
    for cameras in (item for item in root.iter() if _local(item.tag) == "Cameras"):
        # Devices/Cameras holds the settings; System/Cameras only identifies the camera.
        candidate = _find(cameras, "Camera")
        if candidate is not None and _find(candidate, "ShutterTiming") is not None:
            camera = candidate
            break
    if camera is None:
        camera = root
    exposure = _text(camera, "ShutterTiming", "ExposureTime")
    exposure_seconds = float(exposure) / 1000.0 if exposure is not None else None
    if exposure_seconds is not None and not (np.isfinite(exposure_seconds) and exposure_seconds > 0):
        raise ValueError("The file contains an invalid exposure time")

    regions = ()
    selection_root = _find(camera, "ReadoutControl", "RegionsOfInterest")
    selection = _text(selection_root, "Selection")
    if selection == "CustomRegions":
        custom = _find(selection_root, "CustomRegions")
        regions = tuple(_region(item) for item in (custom if custom is not None else ())
                        if _local(item.tag) == "RegionOfInterest")
    elif selection in ("FullSensor", "BinnedSensor", "LineSensor") and sensor_size is not None:
        width, height = sensor_size
        x_binning = y_binning = 1
        if selection == "BinnedSensor":
            x_binning = int(_text(selection_root, "BinnedSensor", "XBinning") or 1)
            y_binning = int(_text(selection_root, "BinnedSensor", "YBinning") or 1)
        elif selection == "LineSensor":
            y_binning = height
        regions = (SensorRegion(0, width - width % x_binning, x_binning, 0, height - height % y_binning, y_binning),)

    speed = _text(camera, "Adc", "Speed")
    return CameraSetup(exposure_seconds, regions, float(speed) if speed is not None else None,
                       _text(camera, "Adc", "AnalogGain"), _text(camera, "Adc", "Quality"))


def read_experiment_file(path, sensor_size=None) -> CameraSetup:
    """Parse a LightField experiment (.lfe) file, which is XML."""
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as error:
        raise ValueError(f"Could not read {Path(path).name}: {error}") from error
    return camera_setup_from_xml(root, sensor_size)


def read_reference(path) -> SpeReference:
    """Wavelength axis and readout regions from a LightField SPE 3.0 file."""
    path = Path(path)
    try:
        with path.open("rb") as file:
            header = file.read(HEADER_BYTES)
            if len(header) < HEADER_BYTES:
                raise ValueError("file is too short")
            offset = int(np.frombuffer(header, np.uint64, 1, 678)[0])
            if offset < HEADER_BYTES:
                raise ValueError("it has no SPE 3.0 footer (save it from LightField 4 or later)")
            file.seek(offset)
            root = ElementTree.fromstring(file.read())
    except (OSError, ElementTree.ParseError, ValueError) as error:
        raise ValueError(f"{path.name} cannot be used as a wavelength reference: {error}") from error
    calibrations = _find(root, "Calibrations")
    values = _text(calibrations, "WavelengthMapping", "Wavelength")
    sensor = _find(calibrations, "SensorInformation")
    if values is None or sensor is None:
        raise ValueError(f"{path.name} has no wavelength calibration; choose a spectrum saved with the spectrograph")
    wavelengths = np.array([float(value) for value in values.split(",")])
    width, height = int(sensor.attrib["width"]), int(sensor.attrib["height"])
    if wavelengths.size != width:
        raise ValueError(f"{path.name} has {wavelengths.size} wavelengths for a {width}-column sensor")
    mapped = tuple(_region(item) for item in calibrations if _local(item.tag) == "SensorMapping")
    setup = camera_setup_from_xml(root, (width, height))
    if mapped:  # what was actually saved wins over what was requested
        setup = CameraSetup(setup.exposure_seconds, mapped, setup.adc_speed_mhz,
                            setup.adc_analog_gain, setup.adc_quality)
    validate_regions(setup.regions, width, height)
    return SpeReference(path, width, height, wavelengths, setup)


def validate_regions(regions, sensor_width, sensor_height) -> None:
    """The saved image stacks the regions, so they must share columns and not overlap."""
    if not regions:
        raise ValueError("No readout region is defined")
    first = regions[0]
    previous_end = 0
    for region in regions:
        if region.x + region.width > sensor_width or region.y + region.height > sensor_height:
            raise ValueError(f"Readout region exceeds the {sensor_width}x{sensor_height} sensor")
        if (region.x, region.width, region.x_binning) != (first.x, first.width, first.x_binning):
            raise ValueError("All readout regions must use the same columns")
        if region.y < previous_end:
            raise ValueError("Readout regions must be listed top to bottom without overlapping")
        previous_end = region.y + region.height


def region_wavelengths(sensor_wavelengths_nm, regions) -> np.ndarray:
    first = regions[0]
    selected = np.asarray(sensor_wavelengths_nm, dtype=float)[first.x:first.x + first.width]
    if selected.size != first.width:
        raise ValueError("Readout region lies outside the reference wavelength calibration")
    return selected.reshape(first.columns, first.x_binning).mean(axis=1)


def readout_window(regions) -> tuple[int, int, int, int]:
    """One sensor rectangle (x_start, x_end, y_start, y_end) covering every region."""
    first = regions[0]
    return first.x, first.x + first.width, regions[0].y, regions[-1].y + regions[-1].height


def assemble_image(window_frame, regions) -> np.ndarray:
    """Cut the regions out of an unbinned readout window and stack them; bin by summing."""
    frame = np.asarray(window_frame)
    x_start, x_end, y_start, y_end = readout_window(regions)
    if frame.shape != (y_end - y_start, x_end - x_start):
        raise ValueError(f"Camera returned {frame.shape[1]}x{frame.shape[0]} pixels; "
                         f"expected {x_end - x_start}x{y_end - y_start}")
    bands = []
    for region in regions:
        band = frame[region.y - y_start:region.y - y_start + region.height]
        if region.x_binning > 1 or region.y_binning > 1:
            band = band.astype(np.uint32).reshape(region.rows, region.y_binning,
                                                  region.columns, region.x_binning).sum(axis=(1, 3))
        bands.append(band)
    return np.vstack(bands)


_PIXEL_FORMATS = {np.dtype(np.uint16): (3, "MonochromeUnsigned16"),
                  np.dtype(np.uint32): (8, "MonochromeUnsigned32"),
                  np.dtype(np.float32): (0, "MonochromeFloating32")}


def write_spe(path, frames, sensor_wavelengths_nm, regions, sensor_size, exposure_seconds,
              camera_model="PIXIS", software="EPL Laser Heating Control", created=None) -> Path:
    """Write frames (frame, row, column) as SPE 3.0 with a wavelength calibration."""
    path = Path(path)
    frames = np.asarray(frames)
    if frames.ndim == 2:
        frames = frames[np.newaxis]
    if frames.dtype not in _PIXEL_FORMATS:
        frames = frames.astype(np.uint16 if np.issubdtype(frames.dtype, np.integer)
                               and frames.min() >= 0 and frames.max() <= 0xFFFF else np.float32)
    data_type, pixel_format = _PIXEL_FORMATS[frames.dtype]
    count, rows, columns = frames.shape
    sensor_width, sensor_height = sensor_size
    validate_regions(regions, sensor_width, sensor_height)
    if rows != sum(region.rows for region in regions) or columns != regions[0].columns:
        raise ValueError("Frame size does not match the readout regions")
    wavelengths = np.asarray(sensor_wavelengths_nm, dtype=float)
    if wavelengths.size != sensor_width:
        raise ValueError("One wavelength is required for each sensor column")
    created = created or time.strftime("%Y-%m-%dT%H:%M:%S") + time.strftime("%z")[:3] + ":" + time.strftime("%z")[3:]
    item = frames.dtype.itemsize
    frame_bytes = rows * columns * item

    def attributes(region):
        return (f'x="{region.x}" y="{region.y}" width="{region.width}" height="{region.height}" '
                f'xBinning="{region.x_binning}" yBinning="{region.y_binning}"')

    blocks = "".join(
        f'<DataBlock type="Region" count="1" width="{region.columns}" height="{region.rows}" '
        f'size="{region.rows * region.columns * item}" stride="{region.rows * region.columns * item}" '
        f'calibrations="2,{index + 3}"/>' for index, region in enumerate(regions))
    mappings = "".join(f'<SensorMapping id="{index + 3}" {attributes(region)}/>'
                       for index, region in enumerate(regions))
    rois = "".join(f'<RegionOfInterest id="{index}" {attributes(region)}/>'
                   for index, region in enumerate(regions))
    footer = (
        f'<SpeFormat version="3.0" xmlns="{SPE_NAMESPACE}">'
        f'<DataFormat><DataBlock type="Frame" count="{count}" pixelFormat="{pixel_format}" '
        f'size="{frame_bytes}" stride="{frame_bytes}">{blocks}</DataBlock></DataFormat>'
        f'<Calibrations><WavelengthMapping id="1" date={quoteattr(created)} orientation="Normal">'
        f'<Wavelength xml:space="preserve">{",".join(repr(float(value)) for value in wavelengths)}</Wavelength>'
        f'</WavelengthMapping>'
        f'<SensorInformation id="2" orientation="Normal" width="{sensor_width}" height="{sensor_height}"/>'
        f'{mappings}</Calibrations>'
        f'<DataHistories><DataHistory id="1"><Origin software={quoteattr(software)} created={quoteattr(created)}>'
        f'<Experiment xmlns="{EXPERIMENT_NAMESPACE}" version="11">'
        f'<System><Cameras count="1"><Camera deviceID="1" model={quoteattr(camera_model)}/></Cameras></System>'
        f'<Devices><Cameras count="1"><Camera deviceID="1">'
        f'<ShutterTiming><ExposureTime type="Double">{exposure_seconds * 1000.0!r}</ExposureTime></ShutterTiming>'
        f'<ReadoutControl><RegionsOfInterest><Selection type="RegionsOfInterestSelection">CustomRegions</Selection>'
        f'<CustomRegions type="RegionsOfInterest" count="{len(regions)}">{rois}</CustomRegions>'
        f'</RegionsOfInterest></ReadoutControl>'
        f'<Experiment><Acquisition><FramesToStore type="Int64">{count}</FramesToStore></Acquisition></Experiment>'
        f'</Camera></Cameras></Devices></Experiment></Origin></DataHistory></DataHistories>'
        f'</SpeFormat>').encode("utf-8")

    header = bytearray(HEADER_BYTES)

    def put(offset, dtype, value):
        header[offset:offset + np.dtype(dtype).itemsize] = np.array(value, dtype=dtype).tobytes()

    put(6, np.uint16, sensor_width)       # xDimDet
    put(10, np.float32, exposure_seconds)
    put(18, np.uint16, sensor_height)     # yDimDet
    put(34, np.int16, -1)                 # noscan (obsolete marker)
    put(42, np.uint16, columns)           # xdim
    put(108, np.int16, data_type)
    put(656, np.uint16, rows)             # ydim
    put(658, np.int16, 1)                 # scramble
    put(664, np.int32, -1)                # lnoscan
    put(678, np.uint64, HEADER_BYTES + frames.nbytes)
    put(1446, np.int32, count)
    put(1992, np.float32, 3.0)            # file header version
    put(2996, np.int32, 0x01234567)       # WinView id
    put(4098, np.uint16, 0x5555)          # last value
    temporary = path.with_name(path.name + ".part")
    with temporary.open("wb") as file:
        file.write(header)
        file.write(np.ascontiguousarray(frames).astype(frames.dtype.newbyteorder("<"), copy=False).tobytes())
        file.write(footer)
    temporary.replace(path)  # readers and the folder watcher never see a partial file
    return path
