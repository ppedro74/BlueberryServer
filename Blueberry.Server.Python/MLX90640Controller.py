import array
import math
import sys
import logging
import time
import ctypes
import struct
import threading
import Controller
import TcpServer
import traceback

SCALEALPHA = 0.000001

#Source: Datasheet Page 44
#In case this Tr, temperature is not available and cannot be provided
# it might be replaced by TR ≈ Ta − 8
TA_DIFF = 8 

class MLX90640Exception(Exception):
    def __init__(self, message):
        self.message = message

class MLX90640Parameters:
    def __init__(self):
        self.kVdd = 0					    # int16_t
        self.vdd25 = 0                      # int16_t
        self.KvPTAT = 0.0                   # float
        self.KtPTAT = 0.0                   # float
        self.vPTAT25 = 0                    # uint16_t
        self.alphaPTAT = 0.0                # float
        self.gainEE = 0                     # int16_t
        self.tgc = 0.0                      # float
        self.cpKv = 0.0                     # float
        self.cpKta = 0.0                    # float
        self.resolutionEE = 0               # uint8_t
        self.calibrationModeEE = 0          # uint8_t
        self.KsTa = 0.0                     # float
        self.ksTo = [0.0] * 5               # float[5]
        self.ct = [0] * 5                   # int16_t[5]
        self.alpha = [0] * 768              # uint16_t[768]
        self.alphaScale = 0                 # uint8_t
        self.offset = [0] * 768             # int16_t[768]
        self.kta = [0] * 768                # int8_t[768]
        self.ktaScale = 0                   # uint8_t
        self.kv = [0] * 768                 # int8_t[768]
        self.kvScale = 0                    # uint8_t
        self.cpAlpha = [0.0] * 2            # float[2]
        self.cpOffset = [0] * 2             # int16_t[2]
        self.ilChessC = [0.0] * 3           # float[3]
        self.brokenPixels = [0] * 5         # uint16_t[5]
        self.outlierPixels = [0] * 5        # uint16_t[5]
        return

class MLX90640Controller(Controller.Controller):
    RefreshRates = [0.5, 1, 2, 4, 8, 16, 32, 64]

    def __init__(self, i2c_controller, log_level, tcp_server=None, i2c_address=0x33):
        super().__init__(self.__class__.__name__ + "-" + str(i2c_address), log_level)
        self.i2c_controller = i2c_controller
        self.i2c_address = i2c_address
        self.server = tcp_server
        self.slave = None
        self.shutdown = False
        self.run_thread = None
        self.frame_rate = 1
        self.emissivity = 0.95
        self.frame_index = 0

    def I2CRead(self, startAddress, number_of_words_to_read=1):
        data = self.slave.write_read_data([startAddress >> 8, startAddress & 0x00FF], number_of_words_to_read * 2)
        fmt = ">{}H".format(number_of_words_to_read)
        words = array.array("H", struct.unpack(fmt, data))
        return words[0] if number_of_words_to_read == 1 else words

    def I2CWrite(self, writeAddress, word_data):
        cmd = bytearray(4)
        cmd[0] = writeAddress >> 8
        cmd[1] = writeAddress & 0x00FF
        cmd[2] = word_data >> 8
        cmd[3] = word_data & 0x00FF
        self.slave.write(cmd)

    def DumpEE(self):
        return self.I2CRead(0x2400, 832)

    def ExtractParameters(self, eeData, mlx90640):
        deviceSelect = eeData[10] & 0x0040
        if deviceSelect != 0:
            raise MLX90640Exception("Expected deviceSelect=0")

        self.ExtractVDDParameters(eeData, mlx90640)
        self.ExtractPTATParameters(eeData, mlx90640)
        self.ExtractGainParameters(eeData, mlx90640)
        self.ExtractTgcParameters(eeData, mlx90640)
        self.ExtractResolutionParameters(eeData, mlx90640)
        self.ExtractKsTaParameters(eeData, mlx90640)
        self.ExtractKsToParameters(eeData, mlx90640)
        self.ExtractCPParameters(eeData, mlx90640)
        self.ExtractAlphaParameters(eeData, mlx90640)
        self.ExtractOffsetParameters(eeData, mlx90640)
        self.ExtractKtaPixelParameters(eeData, mlx90640)
        self.ExtractKvPixelParameters(eeData, mlx90640)
        self.ExtractCILCParameters(eeData, mlx90640)
        error = self.ExtractDeviatingPixels(eeData, mlx90640)  
        if error != 0:
            raise MLX90640Exception("ExtractDeviatingPixels error=" + str(error))

        #self.logger.debug("mlx90640=%s", vars(mlx90640))
        return 

    def GetFrameData(self, frameData):
        cnt = 0
        dataReady = 0
        t_start = time.time()
        while dataReady == 0:
            statusRegister = self.I2CRead(0x8000)
            dataReady = statusRegister & 0x0008
            t_end = time.time()
            t_elapsed = t_end - t_start
            if t_elapsed > 5:
                raise MLX90640Exception("Timeout error waiting for dataReady")
            time.sleep(0.05)

        while dataReady != 0 and cnt < 5:
            self.I2CWrite(0x8000, 0x0030)            
            data = self.I2CRead(0x0400, 832)    
            frameData[0:832] = data
            statusRegister = self.I2CRead(0x8000)
            dataReady = statusRegister & 0x0008
            cnt = cnt + 1
    
        if cnt > 4:
            raise MLX90640Exception("Timeout error waiting for dataReady 2")
            return -8
        
        controlRegister1 = self.I2CRead(0x800D)
        frameData[832] = controlRegister1
        frameData[833] = statusRegister & 0x0001
        return frameData[833]    

    #added
    def SetSubPagesMode(self, subPagesMode):
        value = (subPagesMode & 0x01)
        controlRegister1 = self.I2CRead(0x800D)
        value = (controlRegister1 & 0xFFFE) | value
        self.I2CWrite(0x800D, value)        
        return value

    #added
    def GetSubPagesMode(self):
        controlRegister1 = self.I2CRead(0x800D)
        subPagesMode = (controlRegister1 & 0x0001)
        return subPagesMode

    #added
    def SetSubPageRepeat(self, subPageRepeat):
        value = (subPageRepeat & 0x01) << 3
        controlRegister1 = self.I2CRead(0x800D)
        value = (controlRegister1 & 0xFFF7) | value
        self.I2CWrite(0x800D, value)        
        return value

    #added
    def GetSubPageRepeat(self):
        controlRegister1 = self.I2CRead(0x800D)
        subpage = (controlRegister1 & 0x0008) >> 3
        return subpage

    #added
    def SetSubPage(self, subPage):
        value = (subPage & 0x01) << 4
        controlRegister1 = self.I2CRead(0x800D)
        value = (controlRegister1 & 0xFFEF) | value
        self.I2CWrite(0x800D, value)        
        return value

    #added
    def GetSubPage(self):
        controlRegister1 = self.I2CRead(0x800D)
        subpage = (controlRegister1 & 0x0070) >> 4
        return subpage

    #added
    def SetRefreshFrequency(self, frequency):
        refreshRate = MLX90640Controller.RefreshRates.index(frequency)
        self.SetRefreshRate(refreshRate)

    #added
    def GetRefreshFrequency(self):
        refreshRate = self.GetRefreshRate()
        return MLX90640Controller.RefreshRates[refreshRate]
    
    #added
    def InterpolateOutliers(self, frameData, eeData):
        for pixelNumber in range(768):
            broken = eeData[64 + pixelNumber] == 0
            outlier = eeData[64 + pixelNumber] & 0x0001
            if broken:
                val = 0
                count = 0
                if pixelNumber - 33 > 0:
                    val += frameData[pixelNumber - 33]
                    val += frameData[pixelNumber - 31]
                    count += 2
                elif pixelNumber - 31 > 0:
                    val += frameData[pixelNumber - 31]
                    count += 1
            
                if pixelNumber + 33 < 768:
                    val += frameData[pixelNumber + 33]
                    val += frameData[pixelNumber + 31]
                    count += 2
                elif pixelNumber + 31 < 768:
                    val += frameData[pixelNumber + 31]
                    count += 1
            
                frameData[pixelNumber] = int((val / count) * 1.0003)
        return

    #added
    def GetDefectivePixels(self, eeData):
        brokens = []
        outliers = []
        for pixelNumber in range(768):
            broken = eeData[64 + pixelNumber] == 0
            if broken:
                brokens.append(pixelNumber)
            outlier = (eeData[64 + pixelNumber] & 0x0001) == 0x0001
            if broken:
                outliers.append(pixelNumber)
        return brokens, outliers


    def SetResolution(self, resolution):
        value = (resolution & 0x03) << 10
        controlRegister1 = self.I2CRead(0x800D)
        value = (controlRegister1 & 0xF3FF) | value
        self.I2CWrite(0x800D, value)        
        return value

    def GetCurResolution(self):
        controlRegister1 = self.I2CRead(0x800D)
        resolutionRAM = (controlRegister1 & 0x0C00) >> 10
        return resolutionRAM

    def SetRefreshRate(self, refreshRate):
        value = (refreshRate & 0x07) << 7
        controlRegister1 = self.I2CRead(0x800D)
        value = (controlRegister1 & 0xFC7F) | value
        self.I2CWrite(0x800D, value) 
        return value

    def GetRefreshRate(self):
        controlRegister1 = self.I2CRead(0x800D)
        refreshRate = (controlRegister1 & 0x0380) >> 7
        return refreshRate

    def SetInterleavedMode(self):
        controlRegister1 = self.I2CRead(0x800D)
        value = (controlRegister1 & 0xEFFF)
        self.I2CWrite(0x800D, value)
        return value

    def SetChessMode(self):
        controlRegister1 = self.I2CRead(0x800D)
        value = (controlRegister1 | 0x1000)
        self.I2CWrite(0x800D, value)
        return value

    def GetCurMode(self):
        controlRegister1 = self.I2CRead(0x800D)
        modeRAM = (controlRegister1 & 0x1000) >> 12
        return modeRAM 

    def CalculateTo(self, frameData, params, emissivity, tr, result):
        irDataCP = [0] * 2
        alphaCorrR = [0] * 4

        subPage = frameData[833]
        vdd = self.GetVDD(frameData, params)
        ta = self.GetTa(frameData, params)

        ta4 = (ta + 273.15)
        ta4 = ta4 * ta4
        ta4 = ta4 * ta4
        tr4 = (tr + 273.15)
        tr4 = tr4 * tr4
        tr4 = tr4 * tr4
        taTr = tr4 - (tr4 - ta4) / emissivity

        ktaScale = pow(2, params.ktaScale)
        kvScale = pow(2, params.kvScale)
        alphaScale = pow(2, params.alphaScale)

        alphaCorrR[0] = 1 / (1 + params.ksTo[0] * 40)
        alphaCorrR[1] = 1
        alphaCorrR[2] = (1 + params.ksTo[1] * params.ct[2])
        alphaCorrR[3] = alphaCorrR[2] * (1 + params.ksTo[2] * (params.ct[3] - params.ct[2]))

        #---- Gain calculation ----
        gain = frameData[778]
        if gain > 32767:
            gain = gain - 65536
        gain = params.gainEE / gain

        #---- To calculation ----
        mode = (frameData[832] & 0x1000) >> 5
        irDataCP[0] = frameData[776]  
        irDataCP[1] = frameData[808]
        for i in range(2):
            if irDataCP[i] > 32767:
                irDataCP[i] = irDataCP[i] - 65536
            irDataCP[i] = irDataCP[i] * gain
        
        irDataCP[0] = irDataCP[0] - params.cpOffset[0] * (1 + params.cpKta * (ta - 25)) * (1 + params.cpKv * (vdd - 3.3))
        if mode == params.calibrationModeEE:
            irDataCP[1] = irDataCP[1] - params.cpOffset[1] * (1 + params.cpKta * (ta - 25)) * (1 + params.cpKv * (vdd - 3.3))
        else:
            irDataCP[1] = irDataCP[1] - (params.cpOffset[1] + params.ilChessC[0]) * (1 + params.cpKta * (ta - 25)) * (1 + params.cpKv * (vdd - 3.3))
        
        for pixelNumber in range(768):
            ilPattern = int(pixelNumber / 32 - (pixelNumber / 64) * 2)
            chessPattern = ilPattern ^ int(pixelNumber - (pixelNumber / 2) * 2) 
            conversionPattern = ((pixelNumber + 2) / 4 - (pixelNumber + 3) / 4 + (pixelNumber + 1) / 4 - pixelNumber / 4) * (1 - 2 * ilPattern)

            if mode == 0:
                pattern = ilPattern
            else:
                pattern = chessPattern
            
            if pattern == frameData[833]:
                irData = frameData[pixelNumber]
                if irData > 32767:
                    irData = irData - 65536
                irData = irData * gain

                kta = params.kta[pixelNumber] / ktaScale
                kv = params.kv[pixelNumber] / kvScale
                irData = irData - params.offset[pixelNumber] * (1 + kta * (ta - 25)) * (1 + kv * (vdd - 3.3))

                if mode != params.calibrationModeEE:
                    irData = irData + params.ilChessC[2] * (2 * ilPattern - 1) - params.ilChessC[1] * conversionPattern 

                irData = irData - params.tgc * irDataCP[subPage]
                irData = irData / emissivity
            
                alphaCompensated = SCALEALPHA * alphaScale / params.alpha[pixelNumber]
                alphaCompensated = alphaCompensated * (1 + params.KsTa * (ta - 25))
                        
                Sx = alphaCompensated * alphaCompensated * alphaCompensated * (irData + alphaCompensated * taTr)
                Sx = math.sqrt(math.sqrt(Sx)) * params.ksTo[1]            

                To = math.sqrt(math.sqrt(irData / (alphaCompensated * (1 - params.ksTo[1] * 273.15) + Sx) + taTr)) - 273.15                     

                if To < params.ct[1]:
                    _range = 0
                elif To < params.ct[2]:
                    _range = 1            
                elif To < params.ct[3]:
                    _range = 2            
                else:
                    _range = 3            

                To = math.sqrt(math.sqrt(irData / (alphaCompensated * alphaCorrR[_range] * (1 + params.ksTo[_range] * (To - params.ct[_range]))) + taTr)) - 273.15
                        
                result[pixelNumber] = To
            else:
                pass
        return 

    def GetImage(self, frameData, params):
        irDataCP = [0] * 2

        subPage = frameData[833]
        vdd = self.GetVDD(frameData, params)
        ta = self.GetTa(frameData, params)

        ktaScale = pow(2, params.ktaScale)
        kvScale = pow(2, params.kvScale)
        alphaScale = pow(2, params.alphaScale)

        #---- Gain calculation ----
        gain = frameData[778]
        if gain > 32767:
            gain = gain - 65536
        gain = params.gainEE / gain

        #---- Image calculation ----
        mode = (frameData[832] & 0x1000) >> 5
        irDataCP[0] = frameData[776]  
        irDataCP[1] = frameData[808]
        for i in range(2):
            if irDataCP[i] > 32767:
                irDataCP[i] = irDataCP[i] - 65536
            irDataCP[i] = irDataCP[i] * gain
        
        irDataCP[0] = irDataCP[0] - params.cpOffset[0] * (1 + params.cpKta * (ta - 25)) * (1 + params.cpKv * (vdd - 3.3))
        if mode == params.calibrationModeEE:
            irDataCP[1] = irDataCP[1] - params.cpOffset[1] * (1 + params.cpKta * (ta - 25)) * (1 + params.cpKv * (vdd - 3.3))
        else:
            irDataCP[1] = irDataCP[1] - (params.cpOffset[1] + params.ilChessC[0]) * (1 + params.cpKta * (ta - 25)) * (1 + params.cpKv * (vdd - 3.3))
        
        result = [0] * 768
        for pixelNumber in range(768):
            ilPattern = int(pixelNumber / 32 - (pixelNumber / 64) * 2)
            chessPattern = ilPattern ^ int(pixelNumber - (pixelNumber / 2) * 2) 
            conversionPattern = ((pixelNumber + 2) / 4 - (pixelNumber + 3) / 4 + (pixelNumber + 1) / 4 - pixelNumber / 4) * (1 - 2 * ilPattern)

            if mode == 0:
                pattern = ilPattern
            else:
                pattern = chessPattern
            
            if pattern == frameData[833]:
                irData = frameData[pixelNumber]
                if irData > 32767:
                    irData = irData - 65536
                irData = irData * gain

                kta = params.kta[pixelNumber] / ktaScale
                kv = params.kv[pixelNumber] / kvScale
                irData = irData - params.offset[pixelNumber] * (1 + kta * (ta - 25)) * (1 + kv * (vdd - 3.3))

                if mode != params.calibrationModeEE:
                    irData = irData + params.ilChessC[2] * (2 * ilPattern - 1) - params.ilChessC[1] * conversionPattern 

                irData = irData - params.tgc * irDataCP[subPage]
            
                alphaCompensated = params.alpha[pixelNumber]

                image = irData * alphaCompensated

                result[pixelNumber] = image
            else:
                pass
        return result

    def GetVDD(self, frameData, params):
        vdd = frameData[810]
        if vdd > 32767:
            vdd = vdd - 65536
        resolutionRAM = (frameData[832] & 0x0c00) >> 10
        resolutionCorrection = pow(2, params.resolutionEE) / pow(2, resolutionRAM)
        vdd = (resolutionCorrection * vdd - params.vdd25) / params.kVdd + 3.3
        return vdd

    def GetTa(self, frameData, params):
        vdd = self.GetVDD(frameData, params)
        ptat = frameData[800]
        if ptat > 32767:
            ptat = ptat - 65536
        ptatArt = frameData[768]
        if ptatArt > 32767:
            ptatArt = ptatArt - 65536
        ptatArt = (ptat / (ptat * params.alphaPTAT + ptatArt)) * pow(2, 18)
        ta = (ptatArt / (1 + params.KvPTAT * (vdd - 3.3)) - params.vPTAT25)
        ta = ta / params.KtPTAT + 25
        return ta

    def GetSubPageNumber(self, frameData):
        return frameData[833]

    def BadPixelsCorrection(self, pixels, to, mode, params):
        ap = [0] * 4
        pix = 0
        while pixels[pix] != 0xFFFF:
            line = pixels[pix] >> 5
            column = pixels[pix] - (line << 5)
            if mode == 1:
                if line == 0:
                    if column == 0:
                        to[pixels[pix]] = to[33]
                    elif column == 31:
                        to[pixels[pix]] = to[62]                      
                    else:
                        to[pixels[pix]] = (to[pixels[pix] + 31] + to[pixels[pix] + 33]) / 2.0                    
                elif line == 23:
                    if column == 0:
                        to[pixels[pix]] = to[705]
                    elif column == 31:
                        to[pixels[pix]] = to[734]
                    else:
                        to[pixels[pix]] = (to[pixels[pix] - 33] + to[pixels[pix] - 31]) / 2.0
                elif column == 0:
                    to[pixels[pix]] = (to[pixels[pix] - 31] + to[pixels[pix] + 33]) / 2.0
                elif column == 31:
                    to[pixels[pix]] = (to[pixels[pix] - 33] + to[pixels[pix] + 31]) / 2.0
                else:
                    ap[0] = to[pixels[pix] - 33]
                    ap[1] = to[pixels[pix] - 31]
                    ap[2] = to[pixels[pix] + 31]
                    ap[3] = to[pixels[pix] + 33]
                    to[pixels[pix]] = self.GetMedian(ap,4)
            else:
                if column == 0:
                    to[pixels[pix]] = to[pixels[pix] + 1]            
                elif column == 1 or column == 30:
                    to[pixels[pix]] = (to[pixels[pix] - 1] + to[pixels[pix] + 1]) / 2.0                
                elif column == 31:
                    to[pixels[pix]] = to[pixels[pix] - 1]
                else:
                    if self.IsPixelBad(pixels[pix] - 2, params) == 0 and self.IsPixelBad(pixels[pix] + 2, params) == 0:
                        ap[0] = to[pixels[pix] + 1] - to[pixels[pix] + 2]
                        ap[1] = to[pixels[pix] - 1] - to[pixels[pix] - 2]
                        if abs(ap[0]) > abs(ap[1]):
                            to[pixels[pix]] = to[pixels[pix] - 1] + ap[1]
                        else:
                            to[pixels[pix]] = to[pixels[pix] + 1] + ap[0]
                    else:
                        to[pixels[pix]] = (to[pixels[pix] - 1] + to[pixels[pix] + 1]) / 2.0                    
            pix = pix + 1    
        return

    def ExtractVDDParameters(self, eeData, mlx90640):
        kVdd = (eeData[51] & 0xFF00) >> 8
        if kVdd > 127:
            kVdd = kVdd - 256
        kVdd = 32 * kVdd
        vdd25 = eeData[51] & 0x00FF
        vdd25 = ((vdd25 - 256) << 5) - 8192
        mlx90640.kVdd = kVdd
        mlx90640.vdd25 = vdd25
        return kVdd, vdd25

    def ExtractPTATParameters(self, eeData, mlx90640):
        KvPTAT = (eeData[50] & 0xFC00) >> 10
        if KvPTAT > 31:
            KvPTAT = KvPTAT - 64
        KvPTAT = KvPTAT / 4096
        KtPTAT = eeData[50] & 0x03FF
        if KtPTAT > 511:
            KtPTAT = KtPTAT - 1024
        KtPTAT = KtPTAT / 8
        vPTAT25 = eeData[49]
        alphaPTAT = (eeData[16] & 0xF000) / pow(2, 14) + 8.0
        mlx90640.KvPTAT = KvPTAT
        mlx90640.KtPTAT = KtPTAT    
        mlx90640.vPTAT25 = vPTAT25
        mlx90640.alphaPTAT = alphaPTAT
        return alphaPTAT
    
    
    def ExtractGainParameters(self, eeData, mlx90640):
        gainEE = eeData[48]
        if gainEE > 32767:
            gainEE = gainEE - 65536
        mlx90640.gainEE = gainEE
        return gainEE

    
    def ExtractTgcParameters(self, eeData, mlx90640):
        tgc = eeData[60] & 0x00FF
        if tgc > 127:
            tgc = tgc - 256
        tgc = tgc / 32.0
        mlx90640.tgc = tgc  
        return tgc

    def ExtractResolutionParameters(self, eeData, mlx90640):
        resolutionEE = (eeData[56] & 0x3000) >> 12
        mlx90640.resolutionEE = resolutionEE
        return resolutionEE

    def ExtractKsTaParameters(self, eeData, mlx90640):
        KsTa = (eeData[60] & 0xFF00) >> 8
        if KsTa > 127:
            KsTa = KsTa - 256
        KsTa = KsTa / 8192.0
        mlx90640.KsTa = KsTa
        return KsTa
    
    def ExtractKsToParameters(self, eeData, mlx90640):
        step = ((eeData[63] & 0x3000) >> 12) * 10

        mlx90640.ct[0] = -40
        mlx90640.ct[1] = 0
        mlx90640.ct[2] = (eeData[63] & 0x00F0) >> 4
        mlx90640.ct[3] = (eeData[63] & 0x0F00) >> 8

        mlx90640.ct[2] = mlx90640.ct[2] * step
        mlx90640.ct[3] = mlx90640.ct[2] + mlx90640.ct[3] * step
        mlx90640.ct[4] = 400

        KsToScale = (eeData[63] & 0x000F) + 8
        KsToScale = 1 << KsToScale

        mlx90640.ksTo[0] = eeData[61] & 0x00FF
        mlx90640.ksTo[1] = (eeData[61] & 0xFF00) >> 8
        mlx90640.ksTo[2] = eeData[62] & 0x00FF
        mlx90640.ksTo[3] = (eeData[62] & 0xFF00) >> 8
        for i in range(4):
            if mlx90640.ksTo[i] > 127:
                mlx90640.ksTo[i] = mlx90640.ksTo[i] - 256
            mlx90640.ksTo[i] = mlx90640.ksTo[i] / KsToScale
        
        mlx90640.ksTo[4] = -0.0002
        return mlx90640.ksTo, mlx90640.ct

    def ExtractAlphaParameters(self, eeData, mlx90640):
        accRow = [0] * 24
        accColumn = [0] * 32
        alphaTemp = [0] * 768

        accRemScale = eeData[32] & 0x000F
        accColumnScale = (eeData[32] & 0x00F0) >> 4
        accRowScale = (eeData[32] & 0x0F00) >> 8
        alphaScale = ((eeData[32] & 0xF000) >> 12) + 30
        alphaRef = eeData[33]

        for i in range(6):
            p = i * 4
            accRow[p + 0] = (eeData[34 + i] & 0x000F)
            accRow[p + 1] = (eeData[34 + i] & 0x00F0) >> 4
            accRow[p + 2] = (eeData[34 + i] & 0x0F00) >> 8
            accRow[p + 3] = (eeData[34 + i] & 0xF000) >> 12
            
        for i in range(24):
            if accRow[i] > 7:
                accRow[i] = accRow[i] - 16

        for i in range(8):
            p = i * 4
            accColumn[p + 0] = (eeData[40 + i] & 0x000F)
            accColumn[p + 1] = (eeData[40 + i] & 0x00F0) >> 4
            accColumn[p + 2] = (eeData[40 + i] & 0x0F00) >> 8
            accColumn[p + 3] = (eeData[40 + i] & 0xF000) >> 12

        for i in range(32):
            if accColumn[i] > 7:
                accColumn[i] = accColumn[i] - 16
                
        for i in range(24):
            for j in range(32):
                p = 32 * i + j
                alphaTemp[p] = (eeData[64 + p] & 0x03F0) >> 4
                if alphaTemp[p] > 31:
                    alphaTemp[p] = alphaTemp[p] - 64

                alphaTemp[p] = alphaTemp[p] * (1 << accRemScale)
                alphaTemp[p] = (alphaRef + (accRow[i] << accRowScale) + (accColumn[j] << accColumnScale) + alphaTemp[p])
                alphaTemp[p] = alphaTemp[p] / pow(2, alphaScale)
                alphaTemp[p] = alphaTemp[p] - mlx90640.tgc * (mlx90640.cpAlpha[0] + mlx90640.cpAlpha[1]) / 2
                alphaTemp[p] = SCALEALPHA / alphaTemp[p]

        temp = alphaTemp[0]
        for i in range(768):
            if alphaTemp[i] > temp:
                temp = alphaTemp[i]
        
        alphaScale = 0
        while temp < 32768:
            temp = temp * 2
            alphaScale = alphaScale + 1
    
        for i in range(768):
            temp = alphaTemp[i] * pow(2, alphaScale)
            mlx90640.alpha[i] = (temp + 0.5)
    
        mlx90640.alphaScale = alphaScale   
        return mlx90640.alphaScale, mlx90640.alpha

    def ExtractOffsetParameters(self, eeData, mlx90640):
        occRow = [0] * 24
        occColumn = [0] * 32
        
        occRemScale = (eeData[16] & 0x000F)
        occColumnScale = (eeData[16] & 0x00F0) >> 4
        occRowScale = (eeData[16] & 0x0F00) >> 8
        offsetRef = eeData[17]
        if offsetRef > 32767:
            offsetRef = offsetRef - 65536

        for i in range(6):
            p = i * 4 
            occRow[p + 0] = (eeData[18 + i] & 0x000F) 
            occRow[p + 1] = (eeData[18 + i] & 0x00F0) >> 4 
            occRow[p + 2] = (eeData[18 + i] & 0x0F00) >> 8 
            occRow[p + 3] = (eeData[18 + i] & 0xF000) >> 12 

        for i in range(24):
            if occRow[i] > 7:
                occRow[i] = occRow[i] - 16 

        for i in range(8):
            p = i * 4 
            occColumn[p + 0] = (eeData[24 + i] & 0x000F) 
            occColumn[p + 1] = (eeData[24 + i] & 0x00F0) >> 4 
            occColumn[p + 2] = (eeData[24 + i] & 0x0F00) >> 8 
            occColumn[p + 3] = (eeData[24 + i] & 0xF000) >> 12 

        for i in range(32):
            if occColumn[i] > 7:
                occColumn[i] = occColumn[i] - 16 

        for i in range(24):
            for j in range(32):
                p = 32 * i + j 
                mlx90640.offset[p] = (eeData[64 + p] & 0xFC00) >> 10 
                if mlx90640.offset[p] > 31:
                    mlx90640.offset[p] = mlx90640.offset[p] - 64 
                
                mlx90640.offset[p] = mlx90640.offset[p] * (1 << occRemScale) 
                mlx90640.offset[p] = (offsetRef + (occRow[i] << occRowScale) + (occColumn[j] << occColumnScale) + mlx90640.offset[p]) 
        return mlx90640.offset

    def ExtractKtaPixelParameters(self, eeData, mlx90640):
        KtaRC = [0] * 4
        ktaTemp = [0] * 768
        
        KtaRoCo = (eeData[54] & 0xFF00) >> 8
        if KtaRoCo > 127:
            KtaRoCo = KtaRoCo - 256
        KtaRC[0] = KtaRoCo

        KtaReCo = (eeData[54] & 0x00FF)
        if KtaReCo > 127:
            KtaReCo = KtaReCo - 256
        KtaRC[2] = KtaReCo

        KtaRoCe = (eeData[55] & 0xFF00) >> 8
        if KtaRoCe > 127:
            KtaRoCe = KtaRoCe - 256
        KtaRC[1] = KtaRoCe

        KtaReCe = (eeData[55] & 0x00FF)
        if KtaReCe > 127:
            KtaReCe = KtaReCe - 256
        KtaRC[3] = KtaReCe

        ktaScale1 = ((eeData[56] & 0x00F0) >> 4) + 8
        ktaScale2 = (eeData[56] & 0x000F)

        for i in range(24):
            for j in range(32):
                p = 32 * i + j
                split = int(2 * (p / 32 - (p / 64) * 2) + p % 2)
                ktaTemp[p] = (eeData[64 + p] & 0x000E) >> 1
                if ktaTemp[p] > 3:
                    ktaTemp[p] = ktaTemp[p] - 8
                ktaTemp[p] = ktaTemp[p] * (1 << ktaScale2)
                ktaTemp[p] = KtaRC[split] + ktaTemp[p]
                ktaTemp[p] = ktaTemp[p] / pow(2, ktaScale1)
                #ktaTemp[p] = ktaTemp[p] * mlx90640.offset[p]

        temp = abs(ktaTemp[0])
        for i in range(24):
            if abs(ktaTemp[i]) > temp:
                temp = abs(ktaTemp[i])
    
        ktaScale1 = 0
        while temp < 64:
            temp = temp * 2
            ktaScale1 = ktaScale1 + 1
            if temp == 0:
                raise MLX90640Exception("Temp is 0")
     
        for i in range(768):
            temp = ktaTemp[i] * pow(2, ktaScale1)
            if temp < 0:
                mlx90640.kta[i] = (temp - 0.5)
            else:
                mlx90640.kta[i] = (temp + 0.5)
    
        mlx90640.ktaScale = ktaScale1
        return mlx90640.ktaScale, mlx90640.kta

    def ExtractKvPixelParameters(self, eeData, mlx90640):
        kvTemp = [0] * 768
        KvT = [0] * 4
        
        KvRoCo = (eeData[52] & 0xF000) >> 12
        if KvRoCo > 7:
            KvRoCo = KvRoCo - 16
        KvT[0] = KvRoCo

        KvReCo = (eeData[52] & 0x0F00) >> 8
        if KvReCo > 7:
            KvReCo = KvReCo - 16
        KvT[2] = KvReCo

        KvRoCe = (eeData[52] & 0x00F0) >> 4
        if KvRoCe > 7:
            KvRoCe = KvRoCe - 16
        KvT[1] = KvRoCe

        KvReCe = (eeData[52] & 0x000F)
        if KvReCe > 7:
            KvReCe = KvReCe - 16
        KvT[3] = KvReCe

        kvScale = (eeData[56] & 0x0F00) >> 8
        for i in range(24):
            for j in range(32):
                p = 32 * i + j
                split = int(2 * (p / 32 - (p / 64) * 2) + p % 2)
                kvTemp[p] = KvT[split]
                kvTemp[p] = kvTemp[p] / pow(2,kvScale)
                #kvTemp[p] = kvTemp[p] * mlx90640.offset[p]

        temp = abs(kvTemp[0])
        for i in range(768):
            if abs(kvTemp[i]) > temp:
                temp = abs(kvTemp[i])
    
        kvScale = 0
        while temp < 64:
            temp = temp * 2
            kvScale = kvScale + 1
     
        for i in range(768):
            temp = kvTemp[i] * pow(2, kvScale)
            if temp < 0:
                mlx90640.kv[i] = (temp - 0.5)
            else:
                mlx90640.kv[i] = (temp + 0.5)
        mlx90640.kvScale = kvScale
        return kvScale, mlx90640.kv

    def ExtractCPParameters(self, eeData, mlx90640):
        alphaSP = [0] * 2 
        offsetSP = [0] * 2
        
        alphaScale = ((eeData[32] & 0xF000) >> 12) + 27
        
        offsetSP[0] = (eeData[58] & 0x03FF)
        if offsetSP[0] > 511:
            offsetSP[0] = offsetSP[0] - 1024
        
        offsetSP[1] = (eeData[58] & 0xFC00) >> 10
        if offsetSP[1] > 31:
            offsetSP[1] = offsetSP[1] - 64
            
        offsetSP[1] = offsetSP[1] + offsetSP[0]
        
        alphaSP[0] = (eeData[57] & 0x03FF)
        if alphaSP[0] > 511:
            alphaSP[0] = alphaSP[0] - 1024
        
        alphaSP[0] = alphaSP[0] / pow(2, alphaScale)
        
        alphaSP[1] = (eeData[57] & 0xFC00) >> 10
        if alphaSP[1] > 31:
            alphaSP[1] = alphaSP[1] - 64
            
        alphaSP[1] = (1 + alphaSP[1] / 128) * alphaSP[0]
        
        cpKta = (eeData[59] & 0x00FF)
        if cpKta > 127:
            cpKta = cpKta - 256
        
        ktaScale1 = ((eeData[56] & 0x00F0) >> 4) + 8
        mlx90640.cpKta = cpKta / pow(2, ktaScale1)
        
        cpKv = (eeData[59] & 0xFF00) >> 8
        if cpKv > 127:
            cpKv = cpKv - 256
        
        kvScale = (eeData[56] & 0x0F00) >> 8
        mlx90640.cpKv = cpKv / pow(2, kvScale)
        
        mlx90640.cpAlpha[0] = alphaSP[0]
        mlx90640.cpAlpha[1] = alphaSP[1]
        mlx90640.cpOffset[0] = offsetSP[0]
        mlx90640.cpOffset[1] = offsetSP[1]
        return mlx90640.cpKta, mlx90640.cpKv, mlx90640.cpAlpha, mlx90640.cpOffset

    def ExtractCILCParameters(self, eeData, mlx90640):
        ilChessC = [0] * 3
        
        calibrationModeEE = (eeData[10] & 0x0800) >> 4
        calibrationModeEE = calibrationModeEE ^ 0x80
        
        ilChessC[0] = (eeData[53] & 0x003F)
        if ilChessC[0] > 31:
            ilChessC[0] = ilChessC[0] - 64
        ilChessC[0] = ilChessC[0] / 16.0
        
        ilChessC[1] = (eeData[53] & 0x07C0) >> 6
        if ilChessC[1] > 15:
            ilChessC[1] = ilChessC[1] - 32
        ilChessC[1] = ilChessC[1] / 2.0
        
        ilChessC[2] = (eeData[53] & 0xF800) >> 11
        if ilChessC[2] > 15:
            ilChessC[2] = ilChessC[2] - 32
        ilChessC[2] = ilChessC[2] / 8.0
        
        mlx90640.calibrationModeEE = calibrationModeEE
        mlx90640.ilChessC[0] = ilChessC[0]
        mlx90640.ilChessC[1] = ilChessC[1]
        mlx90640.ilChessC[2] = ilChessC[2]
        
        return mlx90640.ilChessC, mlx90640.calibrationModeEE

    def ExtractDeviatingPixels(self, eeData, mlx90640):
        pixCnt = 0
        brokenPixCnt = 0
        outlierPixCnt = 0
        warn = 0

        for pixCnt in range(5):
            mlx90640.brokenPixels[pixCnt] = 0xFFFF
            mlx90640.outlierPixels[pixCnt] = 0xFFFF

        pixCnt = 0    
        while (pixCnt < 768 and brokenPixCnt < 5 and outlierPixCnt < 5):
            if eeData[pixCnt + 64] == 0:
                mlx90640.brokenPixels[brokenPixCnt] = pixCnt
                brokenPixCnt = brokenPixCnt + 1
            elif eeData[pixCnt + 64] & 0x0001 != 0:
                mlx90640.outlierPixels[outlierPixCnt] = pixCnt
                outlierPixCnt = outlierPixCnt + 1
            pixCnt = pixCnt + 1

        if brokenPixCnt > 4:  
            warn = -3
        elif outlierPixCnt > 4:  
            warn = -4
        elif brokenPixCnt + outlierPixCnt > 4:  
            warn = -5
        else:
            for pixCnt in range(brokenPixCnt):
                for i in range(pixCnt + 1,brokenPixCnt):
                    warn = self.CheckAdjacentPixels(mlx90640.brokenPixels[pixCnt], mlx90640.brokenPixels[i])
                    if warn != 0:
                        return warn

            for pixCnt in range(outlierPixCnt):
                for i in range(pixCnt + 1,outlierPixCnt):
                    warn = self.CheckAdjacentPixels(mlx90640.outlierPixels[pixCnt], mlx90640.outlierPixels[i])
                    if warn != 0:
                        return warn

            for pixCnt in range(brokenPixCnt):
                for i in range(outlierPixCnt):
                    warn = self.CheckAdjacentPixels(mlx90640.brokenPixels[pixCnt], mlx90640.outlierPixels[i])
                    if warn != 0:
                        return warn
                        
        return warn

    def CheckAdjacentPixels(self, pix1, pix2):
        pixPosDif = pix1 - pix2
        if pixPosDif > -34 and pixPosDif < -30:
            return -6
        if pixPosDif > -2 and pixPosDif < 2:
            return -6
        if pixPosDif > 30 and pixPosDif < 34:
            return -6
        return 0    

    def GetMedian(self, values, n):
        for i in range(n - 1):
            for j in range(i + 1,n):
                if values[j] < values[i]: 
                    temp = values[i]
                    values[i] = values[j]
                    values[j] = temp
        if n % 2 == 0: 
            return (values[n / 2] + values[n / 2 - 1]) / 2.0
        else: 
            return values[n / 2]

    def IsPixelBad(self, pixel, params):
        for i in range(5):
            if pixel == params.outlierPixels[i] or pixel == params.brokenPixels[i]:
                return 1
        return 0     

    def readPixels(self):
        subPage = self.GetFrameData(self.frame)
        ta = self.GetTa(self.frame, self.mlx90640)
        tr = ta - TA_DIFF
        self.CalculateTo(self.frame, self.mlx90640, self.emissivity, tr, self.to)
        self.logger.debug("ix=%s subPage=%s ta=%s", self.frame_index, subPage, ta)

        subPage = self.GetFrameData(self.frame)
        ta = self.GetTa(self.frame, self.mlx90640)
        tr = ta - TA_DIFF
        self.CalculateTo(self.frame, self.mlx90640, self.emissivity, tr, self.to)
        self.logger.debug("ix=%s subPage=%s ta=%s", self.frame_index, subPage, ta)

        if self.requires_fix:
            self.InterpolateOutliers(self.frame, self.eeData)
        
        self.frame_index += 1

        pixels = array.array('f', [0] * (32 * 24))
        pixel_number = 0
        for y in range(0, 24 * 32, 32):
            for x in reversed(range(32)):
                pixels[pixel_number] = self.to[y + x]
                pixel_number += 1

        #pixels = [0] * 32 * 24
        #pixel_number = 0
        #for x in range(32):
        #    for y in range(24):
        #        pixels[pixel_number] = self.to[32 * (23 - y) + x]
        #        pixel_number += 1

        return pixels

    def start(self):
        self.slave = self.i2c_controller.get_slave(self.i2c_address)

        subPagesMode = 1
        self.SetSubPagesMode(subPagesMode)
        subPageRepeat = 0
        self.SetSubPageRepeat(subPageRepeat)
        self.SetRefreshFrequency(self.frame_rate)
        resolution = 0x03
        self.SetResolution(resolution)
        mode = 1
        if mode == 1:
            self.SetChessMode()
        else:
            self.SetInterleavedMode()
        # --- validate config ----
        value = self.GetSubPagesMode()
        if value != subPagesMode:
            self.logger.warning("GetSubPagesMode expected=%s value=%s", subPagesMode, value)
        value = self.GetSubPageRepeat()
        if value != subPageRepeat:
            self.logger.warning("GetSubPageRepeat expected=%s value=%s", subPageRepeat, value)
        value = self.GetRefreshFrequency()
        if value != self.frame_rate:
            self.logger.warning("GetRefreshFrequency expected=%s value=%s", frequency, value)
        value = self.GetCurResolution()                                                                                                 
        if value != resolution:
            self.logger.warning("GetCurResolution expected=%s value=%s", resolution, value)
        value = self.GetCurMode()
        if value != mode:
            self.logger.warning("GetCurMode expected=%s value=%s", mode, value)

        value = self.GetSubPage()
        self.logger.debug("GetSubPage value=%s", value)

        self.eeData = self.DumpEE()
        #for ix in range(32):
        #    print("ix={0} {1}".format(ix, self.eeData[ix]))

        brokens, outliers = self.GetDefectivePixels(self.eeData)
        self.requires_fix = len(brokens) > 0 or len(outliers) > 0
        if self.requires_fix:
            self.logger.warning("pixels brokens=%s outliers=%s", brokens, outliers)
        self.mlx90640 = MLX90640Parameters()
        self.ExtractParameters(self.eeData, self.mlx90640)
        self.frame = array.array('H', [0] * 834)
        self.to = array.array('f', [0] * 768)

        self.shutdown = False
        if not self.server is None:
            self.run_thread = threading.Thread(target=self.run, args=())
            self.run_thread.start()
        return 
    
    def run(self):
        self.logger.debug("running thread:%s", threading.current_thread().getName())
        try:
            self.main()
        except Exception as ex:
            self.shutdown = True
            self.logger.debug("exception %s", ex)
        try:
            self.run_end()
        except Exception as ex:
            self.logger.debug("end exception %s", ex)
            traceback.print_exc()
        self.logger.debug("terminated")

    def stop(self):
        if self.shutdown:
            self.logger.warning("Already stopped")
            return
        self.logger.debug("stopping")
        self.shutdown = True
        if self.run_thread is not None:
            self.logger.debug("join th:%s", self.run_thread.getName())
            self.run_thread.join()
        self.slave.close()

    def run_end(self):
        pass

    def main(self):
        frame_rate_delay = 1 / self.frame_rate
        last_frame_time = 0
        while not self.shutdown:
            if last_frame_time != 0:
                delay = time.time() - last_frame_time
                if delay < frame_rate_delay:
                    time.sleep(frame_rate_delay - delay)
            pixels = self.readPixels()
            data = (ctypes.c_float * len(pixels))()
            data[:] = pixels
            data = bytes(data)
            fmt1 = "%sf" % len(pixels)
            data1 = struct.pack(fmt1, *pixels)
            if data1 != data:
                self.logger.error("serialization issues")
            width = 32
            height = 24
            self.server.send_data(width.to_bytes(2, "little"))
            self.server.send_data(height.to_bytes(2, "little"))
            data_len = len(data)
            self.server.send_data(data_len.to_bytes(2, "little"))
            self.server.send_data(data)
            last_frame_time = time.time()
        return
    

class MLX90640TcpServer(TcpServer.TcpServer):
    def __init__(self, address, log_level):
        super().__init__("MLX90640TcpServer", address, log_level)

if __name__ == "__main__":
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.INFO)
    logging.info("Starting test")



    try:
        tcp_server = None
        tcp_server = MLX90640TcpServer(('', 5555), logging.INFO)
        tcp_server.start()

        if sys.platform == "linux" or sys.platform == "linux2":
            import DeviceI2CController
            i2c_com = DeviceI2CController.DeviceI2CController(1, logging.INFO)
        else:
            import FakeI2CController
            i2c_com = FakeI2CController.FakeI2CController(logging.INFO)

        i2c_com.start()
        controller = MLX90640Controller(i2c_com, logging.DEBUG, tcp_server)
        controller.start()

        #pixels = controller.readPixels(True)
        #pixels = controller.readPixels(True)

        input("===> Press Enter to quit...\n")
    except KeyboardInterrupt:
        print("*** Keyboard Interrupt ***")
    except Exception as ex:
        logging.fatal("Exception: %s", ex)
        traceback.print_exc()


    controller.stop()
    if tcp_server is not None:
        tcp_server.stop()
