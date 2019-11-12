import sys
import threading
import logging
import os
import datetime
import time
import socket
import ComponentRegistry
import TcpClient
import EZBProtocol

class EZBTcpClient(TcpClient.TcpClient):
    EZB4V2_FIRMWARE_ID = 2
    BLUEBERRY_FIRMWARE_ID = 18602

    LAST_ANALOG_PORT = 7
    LAST_DIGITAL_PORT = 23
    SYS_THERMAL_ZONE = "/sys/class/thermal/thermal_zone0/temp"

    def __init__(self, server, client_socket, client_address):
        super().__init__("EZBTcpClient", server, client_socket, client_address)

    def main(self):
        while not self.shutdown:
            data = self.recv(1)
            if data is None:
                break

            cmd = data[0]

            if cmd == EZBProtocol.CommandEnum.EZB4:
                data = self.recv(1)
                if data is None:
                    break
                cmdv4 = data[0]

                if cmdv4 == EZBProtocol.CommandV4Enum.SET_LIPO_BATTERY_PROTECTION_STATE:
                    data = self.recv(1)
                    self.logger.debug("EZBProtocol.CommandV4Enum.SET_LIPO_BATTERY_PROTECTION_STATE state=%s", data[0])
            
                elif cmdv4 == EZBProtocol.CommandV4Enum.SET_BATTERY_MONITOR_VOLTAGE:
                    data = self.recv(2)
                    bat_volt = int.from_bytes(data, "little") / 258
                    self.logger.debug("EZBProtocol.CommandV4Enum.SET_BATTERY_MONITOR_VOLTAGE v=%s", bat_volt)

                elif cmdv4 == EZBProtocol.CommandV4Enum.GET_BATTERY_VOLTAGE:
                    self.logger.debug("EZBProtocol.CommandV4Enum.GET_BATTERY_VOLTAGE")
                    bat_volt = 258 * 5
                    self.socket.send(bat_volt.to_bytes(2, "little"))

                elif cmdv4 == EZBProtocol.CommandV4Enum.GET_CPU_TEMPERATURE:
                    self.logger.debug("EZBProtocol.CommandV4Enum.GET_CPU_TEMPERATURE")
                    if os.path.exists(self.SYS_THERMAL_ZONE):
                        f = open(self.SYS_THERMAL_ZONE)
                        cpu_temp = f.read()
                        f.close()
                    else:
                        cpu_temp = 37000
                    cpu_temp2 = int((int(cpu_temp) * 38.209699373057859) / 1000.0)
                    self.socket.send(cpu_temp2.to_bytes(2, "little"))

                elif cmdv4 in [EZBProtocol.CommandV4Enum.UART0_INIT, EZBProtocol.CommandV4Enum.UART1_INIT, EZBProtocol.CommandV4Enum.UART2_INIT]:
                    uart_port = 0 if cmdv4 == EZBProtocol.CommandV4Enum.UART0_INIT else 1 if cmdv4 == EZBProtocol.CommandV4Enum.UART1_INIT else 2
                    data = self.recv(4)
                    if data is None:
                        break
                    bauds = int.from_bytes(data, "little")
                    self.logger.debug("EZBProtocol.CommandV4Enum.UART%s_INIT bauds=%s", uart_port, bauds)
                    com = ComponentRegistry.ComponentRegistry.get_component("uart" + str(uart_port))
                    if com is not None:
                        com.serial.baudrate = bauds

                elif cmdv4 in [EZBProtocol.CommandV4Enum.UART0_WRITE, EZBProtocol.CommandV4Enum.UART1_WRITE, EZBProtocol.CommandV4Enum.UART2_WRITE]:
                    uart_port = 0 if cmdv4 == EZBProtocol.CommandV4Enum.UART0_WRITE else 1 if cmdv4 == EZBProtocol.CommandV4Enum.UART1_WRITE else 2
                   
                    data = self.recv(2)
                    if data is None:
                        break
                    data_len = int.from_bytes(data, "little")
                    data = self.recv(data_len)
                    if data is None:
                        break
                    self.logger.debug("EZBProtocol.CommandV4Enum.UART%s_WRITE len=%s", uart_port, data_len)

                    com = ComponentRegistry.ComponentRegistry.get_component("uart" + str(uart_port))
                    if com is not None:
                        com.write(data)
            
                elif cmdv4 in [EZBProtocol.CommandV4Enum.UART0_AVAILABLE_BYTES, EZBProtocol.CommandV4Enum.UART1_AVAILABLE_BYTES, EZBProtocol.CommandV4Enum.UART2_AVAILABLE_BYTES]:
                    uart_port = 0 if cmdv4 == EZBProtocol.CommandV4Enum.UART0_AVAILABLE_BYTES else 1 if cmdv4 == EZBProtocol.CommandV4Enum.UART1_AVAILABLE_BYTES else 2
                        
                    com = ComponentRegistry.ComponentRegistry.get_component("uart" + str(uart_port))
                    available_bytes = 0 if com is None else com.get_available_bytes()

                    self.logger.debug("EZBProtocol.CommandV4Enum.UART%s_AVAILABLE_BYTES => %s", uart_port, available_bytes)
                    self.socket.send(available_bytes.to_bytes(2, "little"))
            
                elif cmdv4 in [EZBProtocol.CommandV4Enum.UART0_READ, EZBProtocol.CommandV4Enum.UART1_READ, EZBProtocol.CommandV4Enum.UART2_READ]:
                    uart_port = 0 if cmdv4 == EZBProtocol.CommandV4Enum.UART0_READ else 1 if cmdv4 == EZBProtocol.CommandV4Enum.UART1_READ else 2
                    data = self.recv(2)
                    if data is None:
                        break
                    data_len = int.from_bytes(data, "little")
                    self.logger.debug("EZBProtocol.CommandV4Enum.UART%s_READ len=%s", uart_port, data_len)
                    com = ComponentRegistry.ComponentRegistry.get_component("uart" + str(uart_port))
                    data = [] if com is None else com.read(data_len)
                    # bad protocol design!!! no way to send 0 bytes
                    if len(data)>0:
                        self.socket.send(data)
            
                elif cmdv4 == EZBProtocol.CommandV4Enum.SET_I2C_CLOCKSPEED:
                    data = self.recv(4)
                    if data is None:
                        break
                    speed = int.from_bytes(data, "little")
                    self.logger.debug("EZBProtocol.CommandV4Enum.SET_I2C_CLOCKSPEED speed=%s", speed)

                elif cmdv4 == EZBProtocol.CommandV4Enum.SET_UART_CLOCKSPEED:
                    data = self.recv(1)
                    baud_ix = data[0]
                    if data is None:
                        break
                    data = self.recv(2)
                    if data is None:
                        break
                    timming = int.from_bytes(data, "little")
                    self.logger.debug("EZBProtocol.CommandV4Enum.SET_UART_CLOCKSPEED baud_ix=%s timming=%s", baud_ix, timming)
                
                else:
                    self.logger.warning("EZBProtocol.CommandV4Enum %s not handled", cmdv4)

            elif cmd == EZBProtocol.CommandEnum.I2C_WRITE:
                data = self.recv(2)
                if data is None:
                    break
                i2c_addr = data[0] >> 1
                data_len = data[1]
                self.logger.debug("EZBProtocol.CommandEnum.I2C_WRITE addr=%s/%s len=%s", i2c_addr, hex(i2c_addr), data_len)
                data = self.recv(data_len)
                i2c = ComponentRegistry.ComponentRegistry.get_component("i2c")
                if i2c is not None:
                    i2c.write(i2c_addr, data)

            elif cmd == EZBProtocol.CommandEnum.I2C_READ:
                data = self.recv(2)
                if data is None:
                    break
                i2c_addr = data[0] >> 1
                data_len = data[1]
                self.logger.debug("EZBProtocol.CommandEnum.I2C_READ addr=%s/%s len=%s", i2c_addr, hex(i2c_addr), data_len)
                i2c = ComponentRegistry.ComponentRegistry.get_component("i2c")
                if i2c is not None:
                    data = i2c.read(i2c_addr, data_len)
                else:
                    data = bytes(0)

                # bad protocol design!!! no way to send n bytes than requested
                if len(data)<data_len:
                    #pad
                    data += bytearray(data_len - len(data))
                    self.logger.warning("padding requested=%s read=%s", data_len, len(data))
                elif len(data)>data_len:
                    #truncate
                    data = data[0:data_len]
                self.socket.send(bytes(data))

            elif EZBProtocol.CommandEnum.SET_PWM_D0 <= cmd <= EZBProtocol.CommandEnum.SET_PWM_D0 + self.LAST_DIGITAL_PORT:
                port = cmd - EZBProtocol.CommandEnum.SET_PWM_D0
                data = self.recv(1)
                if data is None:
                    break
                duty_cycle = data[0]
                self.logger.debug("EZBProtocol.CommandEnum.SET_PWM port=%s duty_cycle=%s", port, duty_cycle)
                pwm = ComponentRegistry.ComponentRegistry.get_component("P"+str(port))
                if pwm is not None:
                    pwm.set_duty_cycle(duty_cycle)

            elif EZBProtocol.CommandEnum.SET_SERVO_SPEED_D0 <= cmd <= EZBProtocol.CommandEnum.SET_SERVO_SPEED_D0 + self.LAST_DIGITAL_PORT:
                port = cmd - EZBProtocol.CommandEnum.SET_SERVO_SPEED_D0
                data = self.recv(1)
                if data is None:
                    break
                speed = data[0]
                self.logger.debug("EZBProtocol.CommandEnum.SET_PWM port=%s speed=%s", port, speed)
                servo = ComponentRegistry.ComponentRegistry.get_component("S"+str(port))
                if servo is not None:
                    servo.set_speed(speed)

            elif cmd == EZBProtocol.CommandEnum.PING:
                self.logger.debug("EZBProtocol.CommandEnum.PING")
                ping_response = 222
                self.socket.send(ping_response.to_bytes(1, "little"))

            elif EZBProtocol.CommandEnum.SET_DIGITAL_PORT_ON_D0 <= cmd <= EZBProtocol.CommandEnum.SET_DIGITAL_PORT_ON_D0 + self.LAST_DIGITAL_PORT:
                port = cmd - EZBProtocol.CommandEnum.SET_DIGITAL_PORT_ON_D0
                self.logger.debug("EZBProtocol.CommandEnum.SET_DIGITAL_PORT_ON port=%s", port)
                digital = ComponentRegistry.ComponentRegistry.get_component("D"+str(port))
                if digital is not None:
                    digital.set(1)

            elif EZBProtocol.CommandEnum.SET_DIGITAL_PORT_OFF_D0 <= cmd <= EZBProtocol.CommandEnum.SET_DIGITAL_PORT_OFF_D0 + self.LAST_DIGITAL_PORT:
                port = cmd - EZBProtocol.CommandEnum.SET_DIGITAL_PORT_OFF_D0
                self.logger.debug("EZBProtocol.CommandEnum.SET_DIGITAL_PORT_OFF port=%s", port)
                digital = ComponentRegistry.ComponentRegistry.get_component("D"+str(port))
                if digital is not None:
                    digital.set(0)

            elif EZBProtocol.CommandEnum.GET_DIGITAL_PORT_D0 <= cmd <= EZBProtocol.CommandEnum.GET_DIGITAL_PORT_D0 + self.LAST_DIGITAL_PORT:
                port = cmd - EZBProtocol.CommandEnum.GET_DIGITAL_PORT_D0
                self.logger.debug("EZBProtocol.CommandEnum.GET_DIGITAL_PORT port=%s", port)
                digital = ComponentRegistry.ComponentRegistry.get_component("D"+str(port))
                if digital is not None:
                    state = digital.get()
                else:
                    state = 0
                self.socket.send(state.to_bytes(1, "little"))

            elif EZBProtocol.CommandEnum.SET_SERVO_POSITION_D0 <= cmd <= EZBProtocol.CommandEnum.SET_SERVO_POSITION_D0 + self.LAST_DIGITAL_PORT:
                port = cmd - EZBProtocol.CommandEnum.SET_SERVO_POSITION_D0
                data = self.recv(1)
                if data is None:
                    break
                position = data[0]
                self.logger.debug("EZBProtocol.CommandEnum.SET_SERVO_POSITION port=%s position=%s", port, position)
                servo = ComponentRegistry.ComponentRegistry.get_component("S"+str(port))
                if servo is not None:
                    #correct degrees 0-179
                    if position>0:
                        servo.set_position(position-1)
                    else:
                        servo.release()

            elif EZBProtocol.CommandEnum.GET_ADC_VALUE_A0 <= cmd <= EZBProtocol.CommandEnum.GET_ADC_VALUE_A0 + self.LAST_ANALOG_PORT:
                port = cmd - EZBProtocol.CommandEnum.GET_ADC_VALUE_A0
                data = self.recv(1)
                if data is None:
                    break
                self.logger.debug("EZBProtocol.CommandEnum.GET_ADC_VALUE port=%s", port)
                state = 0
                self.socket.send(state.to_bytes(1, "little"))
            
            elif EZBProtocol.CommandEnum.SEND_SERIAL_D0 <= cmd <= EZBProtocol.CommandEnum.SEND_SERIAL_D0 + self.LAST_DIGITAL_PORT:
                port = cmd - EZBProtocol.CommandEnum.SEND_SERIAL_D0
                data = self.recv(1)
                baud_ix = data[0]
                data = self.recv(2)
                data_len = int.from_bytes(data, "little")
                data = self.recv(data_len)
                self.logger.debug("EZBProtocol.CommandEnum.SEND_SERIAL_D0 port=%s baud_ix=%s len=%s", port, baud_ix, data_len)
                state = 0
                self.socket.send(state.to_bytes(1, "little"))

            elif EZBProtocol.CommandEnum.READ_HCSR04_D0 <= cmd <= EZBProtocol.CommandEnum.READ_HCSR04_D0 + self.LAST_DIGITAL_PORT:
                trigger_port = cmd - EZBProtocol.CommandEnum.READ_HCSR04_D0
                data = self.recv(1)
                echo_port = data[0]
                self.logger.debug("EZBProtocol.CommandEnum.READ_HCSR04_D0 trigger_port=%s baud_ix=%s echo_port=%s", trigger_port, echo_port)
                distance_value = 0
                self.socket.send(distance_value.to_bytes(1, "little"))

            elif cmd == EZBProtocol.CommandEnum.GET_FIRMWARE_ID:
                self.logger.debug("EZBProtocol.CommandEnum.GET_FIRMWARE_ID")
                self.socket.send(self.EZB4V2_FIRMWARE_ID.to_bytes(4, "little"))

            elif cmd == EZBProtocol.CommandEnum.SOUND_STREAM_CMD:
                data = self.recv(1)
                if data is None:
                    break
                cmdsnd = data[0]
                if cmdsnd == EZBProtocol.CommandSoundV4Enum.INIT_STOP:
                    self.logger.debug("EZBProtocol.CommandSoundV4Enum.INIT_STOP")
                    audio_player = ComponentRegistry.ComponentRegistry.get_component("audio_player")
                    if audio_player is not None:
                        audio_player.stream_stop()
                        audio_player.stream_init()

                elif cmdsnd == EZBProtocol.CommandSoundV4Enum.LOAD:
                    data = self.recv(2)
                    if data is None:
                        break
                    data_len = int.from_bytes(data, "little")
                    data = self.recv(data_len)
                    if data is None:
                        break
                    self.logger.debug("EZBProtocol.CommandSoundV4Enum.LOAD len=%s", data_len)
                    audio_player = ComponentRegistry.ComponentRegistry.get_component("audio_player")
                    if audio_player is not None:
                        audio_player.stream_load(data)

                elif cmdsnd == EZBProtocol.CommandSoundV4Enum.PLAY:
                    self.logger.debug("EZBProtocol.CommandSoundV4Enum.PLAY")
                    audio_player = ComponentRegistry.ComponentRegistry.get_component("audio_player")
                    if audio_player is not None:
                        audio_player.stream_play()

                else:
                    self.logger.warning("CmdSoundStreamCmd %s not handled", cmdsnd)

            else:
                self.logger.warning("cmd %s not handled", cmd)



