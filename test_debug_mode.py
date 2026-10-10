"""Regression checks for the offline instrument boundary. Run with unittest."""
import unittest
from unittest.mock import patch

import agilis_control
import comms_monitor
import denkovi_serial
import hardware_mode
import laser_communication


class DebugModeTests(unittest.TestCase):
    def setUp(self):
        hardware_mode.configure(debug=True)
        denkovi_serial._debug_relay_states.clear()
        comms_monitor._history.clear()

    def tearDown(self):
        hardware_mode.configure(debug=False)

    def test_debug_controls_never_open_serial_or_network_connections(self):
        with patch('serial.Serial', side_effect=AssertionError('serial I/O')), \
             patch('socket.socket', side_effect=AssertionError('network I/O')):
            agilis_control.piezo_move_relative('COM11', 1, 2, 0, 10)
            agilis_control.piezo_jog_at_speed('COM11', 1, 2, 3)
            agilis_control.piezo_stop('COM11', 1, 2)
            agilis_control.piezo_set_remote_mode()
            denkovi_serial.send_relay_bytes('COM7', 0x81, 0x42)
            denkovi_serial.read_denkovi_status('COM7')
            denkovi_serial.flip_single_relay_status('COM7', 16)
            denkovi_serial.write_relay_state('COM6', '1' * 16)
            for command in ('ABN', 'ABF', 'EMON', 'EMOFF', 'SDC 25'):
                self.assertEqual(laser_communication.laser_send_command('127.0.0.1', command), command + '\r')
            laser_communication.guide_laser_left_on()
            laser_communication.guide_laser_left_off()
            laser_communication.guide_laser_right_on()
            laser_communication.guide_laser_right_off()
            laser_communication.LaserCommunication.laser_send_command_RS232(None, 'COM1', 'EMON')
        self.assertTrue(all('[DEBUG - SIMULATED]' in entry for entry in comms_monitor.get_history()))

    def test_relay_states_round_trip_and_boards_are_independent(self):
        expected = [int(bit) for bit in '1000000101000010']
        denkovi_serial.send_relay_bytes('left', 0x81, 0x42)
        self.assertEqual(denkovi_serial.read_denkovi_status('left'), expected)
        self.assertEqual(denkovi_serial.read_denkovi_status('right'), [0] * 16)
        for relay in (1, 8, 9, 16):
            denkovi_serial.flip_single_relay_status('left', relay)
            expected[relay - 1] ^= 1
            self.assertEqual(denkovi_serial.read_denkovi_status('left'), expected)
        state_copy = denkovi_serial.read_denkovi_status('left')
        state_copy[0] ^= 1
        self.assertEqual(denkovi_serial.read_denkovi_status('left'), expected)
        denkovi_serial.write_relay_state('right', '1' * 16)
        self.assertEqual(denkovi_serial.read_denkovi_status('right'), [1] * 16)
        self.assertEqual(denkovi_serial.read_denkovi_status('left'), expected)

    def test_normal_mode_uses_existing_transports(self):
        hardware_mode.configure()
        self.assertFalse(hardware_mode.is_debug())
        with patch('serial.Serial') as serial_open, patch('socket.socket') as socket_open:
            agilis_control.piezo_stop('COM11', 2, 1)
            serial_open.assert_called_once()
            serial_open.return_value.write.assert_any_call(b'CC2\r\n')
            serial_open.return_value.write.assert_any_call(b'1ST\r\n')
            serial_open.reset_mock()
            denkovi_serial.send_relay_bytes('COM7', 0x81, 0x42)
            serial_open.return_value.write.assert_called_once_with(b'x\x81\x42//')
            serial_open.return_value.read.side_effect = [b'\x81', b'\x42']
            self.assertEqual(denkovi_serial.read_denkovi_status('COM7'),
                             [int(bit) for bit in '1000000101000010'])
            socket_open.return_value.recv.return_value = b'ABN\r'
            self.assertEqual(laser_communication.laser_send_command('127.0.0.1', 'ABN'), 'ABN\r')
            socket_open.return_value.connect.assert_called_once_with(('127.0.0.1', 10001))
            socket_open.return_value.send.assert_called_once_with(b'ABN\r')


if __name__ == '__main__':
    unittest.main()
