# Lantronix Programmer
Multistage programming and testing for Grid Connect products with Lantronix internals

## Installation
### Using git clone
```
$ git clone https://github.com/rdslade/xPico
$ cd xPico
```
### Using downloads
1. Download xPico.zip
2. Unzip or open the file in the desired location

## How to use
The functionality of this program is written in the `viz.py` file. 

The `viz.py` grabs the serial ports to use in programing from the `cfg.txt` file one line at a time. 

### How to add device options
There is a [dictionary](https://www.w3schools.com/python/python_dictionaries.asp) (aka 'map' in Java or C++) in the global section of the program right near the top that defines each device. The dictionary, `deviceOptions`, maps a string (the name of the device or part number) to a custom class object called `Device`. The Device class takes two dictionaries as it's input. One parameter is passed through `firmware_files_` and maps the location of the file to be loaded (e.g. `X6` or `WEB1`) to the path of the file to be loaded. The same structre map is passed through `web_files_` to declare the web files associated with a specific device.

At the time of writing this, there are only two such files existing through in the program and that is the GridConnect firmware for the NET232Plus and the original Lantronix firmware for the NET232Plus, labeled as NET232PlusRecover.

Here is the declaration of `deviceOptions` in full.

```
deviceOptions = {
    "NET232Plus" : Device(firmware_files_ = dict(X6 = r"files/NET232pl_6807GC.rom"), web_files_ = dict(WEB1 = r"files\NET232pl_webm_1902.cob")),
    "NET232PlusRecover" : Device(firmware_files_ = dict(X6 = r"files/Recover/xpico_61001.rom"), web_files_ = dict(WEB1 = r"files/Recover/xpico_webm_2006.cob"))
}
```

Let's say we wanted to add a new device which is named `GC-PART-123`. It has two different firmware files named `files/firmware1.rom` and `files/firmware2.rom` which get programmed at `F1` and `F2` respectivley. Also, it has a single web file named `files/web_file.cob` which is to be programmed at `WEB1`.

In order to include this addition, the `deviceOptions` declaration should be changed to include the above info which would look like the following.

```
deviceOptions = {
    "NET232Plus" : Device(firmware_files_ = dict(X6 = r"files/NET232pl_6807GC.rom"), web_files_ = dict(WEB1 = r"files\NET232pl_webm_1902.cob")),
    "NET232PlusRecover" : Device(firmware_files_ = dict(X6 = r"files/Recover/xpico_61001.rom"), web_files_ = dict(WEB1 = r"files/Recover/xpico_webm_2006.cob")),
    "GC-PART-123" : Device(firmware_files_ = dict(F1 = r"files/firmware1.rom", F2 = r"files/firmware2.rom"), web_files_ = dict(WEB1 = r"files/web_file.cob"))
}
```

### How to run
```
py viz.py
```

