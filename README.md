This code run in AutoIt https://www.autoitscript.com/site/

Chamber_Control controls the Test Equity F4T Thermal Chamber, giving readings of the current temperature and controlling the target temperature setpoint.

DC_Power_Supply controls the Keysight N67... DC Power supply with 4 output channels

FrequencyCounter controls an Agilent Frequency counter with a specific script to have it measure channel 1 for a given number of cycles and calculate Allan Deviation

Oscilloscope_Tek_MSO5 gives a control window into the MSO5 series Tektronics oscilloscope (using the web interface on the scope). It also has a screen capture function

All of these use VISA/SCPI commands to talk to the equipment over the network. The Chamber control uses ModBusTCP as I was having trouble using SCPI commands to control the chamber.

Each of these has a field to enter the IP address of the target device. Next to it is a search button that will search the 192.168.0.x subnet for devices, and give you a selection list.


Manual Test Station Companion

Provides a GUI to control
  MSO5 Oscilloscope via VISA/SCPI
  Test Equity F4T Thermal Chamber via modbustcp
  Agilent DC Power Supply via VISA/SCPI
  Agilent Frequency Counter via VISA/SCPI

Each instrument has a script execution queue so they can be given independent tasks while also queueing the tasks, so they do not attempt to run at the same time confusing the instrument.
A master queue not associated with an instrument can be used to run a script and control all devices as needed (not fully implemented yet).

The VISA/SCPI/Modbus script queue can process conditional flow control statements as well as scpi/modbus requests.

Still very much and "evidently so" a work in progress.  :)

Framework for semi-automated testing - Test Tab template
  Profile ini file lists measurement symbols and signals
    gui tab populated with signals and measurements to be taken
  measurement file with two parts
    scpi commands to set up scope for the measurement
    scpi commands to collect data from the scope and record it into a spreadsheet
    internal variables can be used to set text and other captions in the scope screen
    screen shot can also be taken and saved to an output folder based on the test
  picture and caption files for each measurement to highlight each measurement
    in the timing diagram
Settings tab
  list of common variables to identify device under test
  chamber temperatures list to be tested
  
Goals:
  I2C, SPI, SMBus, Clocks, and other validation tests to be mostly automated.
  
Future goals:
  convert to python using win32 gui elements, or maybe switch to more modern but standard windows gui elements that follow windows themes and color schemes
  
  convert to c++ for full compilation and ~5-50x speed improvement
  