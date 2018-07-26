
# Automated CAN Analyzer
We developed a data analysis program that can be used on all vehicle models. 

This program make entry barriers of automotive security research lower.

The update will be completed on July 22, 2018.

<!--<p align="center">
    <img src="https://cdn.rawgit.com/nbedos/termtosvg/0.3.0/examples/awesome.svg">
</p>
More examples of recordings can be found [here](https://github.com/nbedos/termtosvg/blob/0.3.0/examples/examples.md)
-->
## Dependencies

To use ACA in your application developments, you must have installed the following dependencies before you install ACA:
- <span><a href="https://www.python.org/downloads/" style="text-decoration: none;" ><b> Python 3.7.0 (and later versions)</b></a> </span>
- <span><a href="https://github.com/pyserial/pyserial" style="text-decoration: none;" ><b> pip install pyserial (>=3.4)</b></a> </span>
- <span><a href="http://code.google.com/p/prettytable" style="text-decoration: none;" ><b> pip install prettytable (>=0.7.2)</b></a> </span>
- <span><a href="https://github.com/jmcnamara/XlsxWriter" style="text-decoration: none;" ><b> pip install xlsxwriter (>=1.0.5)</b></a> </span>

## Necessary Equipment

- Arduino UNO REV3 (https://store.arduino.cc/usa/arduino-uno-rev3)
- CAN-BUS Shield (http://wiki.seeedstudio.com/CAN-BUS_Shield_V1.2) 
- DB9 OBD-II Cable (https://www.amazon.com/Serial-OBD-II-Allows-Access-Connector/dp/B01EI7KY10/ref=sr_1_3?ie=UTF8&qid=1532457331&sr=8-3&keywords=OBDII+db9)

## Quick Start

1. <a href='https://www.arduino.cc/en/Main/Software'>Install Arduino IDE (version >= 1.8.5)</a>

2. <a href='https://github.com/comma1/ACA/tree/master/Arduino'>Download Arduino Source Code and Compile</a>

3. Equipp Arduino UNO with CAN Bus Shield as shown in Fig. 1 so that Arduino UNO can communicate through CAN. Connecting OBD-II port cable to DB9 port as shown in Fig. 2, and USB cable to USB 2.0 port of a laptop. 

<div align="center">
  <img src="https://postfiles.pstatic.net/MjAxODA3MjVfMTEx/MDAxNTMyNTI0MDg2OTAw.2zW3lS6XzyU2Vvg-vZqFzHIcTjeszrs1mAQoHZphlb0g.FqMm2BCF8nSjk4Ma8uehfjj3d83KxjbQgGK6_Ot92nEg.PNG.ktw1332/20180725_220754.png?type=w773" width="70%" height="70%"><br>Fig. 1. Arduino UNO with CAN-BUS Shield<br>
</div>
<br>
<div align="center">
  <img src="https://postfiles.pstatic.net/MjAxODA3MjVfMTE3/MDAxNTMyNTIzMzUyNzQ2.oWdyOxjl-UjO9Ddcmz7X9SD-LF3XzXdlZN6xEw-HgNMg.MfXX-3C9NaykKRIPn_IfpRqjmN67BJWXmZkm0seKDF4g.PNG.ktw1332/Arduino.png?type=w773" width="70%" height="70%"><br>Fig. 2. Setting of experiment environment using Arduino and OBD-II cable<br>
</div>
<br>
4. Check COM Ports in Device Manager.
   (In this case, Arduino COM port is COM3.)
<br>
<div align="center">
  <img src="https://postfiles.pstatic.net/MjAxODA3MjZfMjU3/MDAxNTMyNTg5NTc2NTA0.rCEdum4pRS0Fk9q4kSbqbbc8Evln_9w2DVq3tc2T-DYg.SKrRJWJazVj5i7yaPHf06SxFfYjeIuSo52JmSotOan0g.PNG.ktw1332/20180726_161909.png?type=w773" width="70%" height="70%"><br><br>
</div>
<br>
5. Edit [Setting][port] in config.ini
   (In this case, Arduino COM port is COM3.)
<br>
<div align="center">
  <img src="https://postfiles.pstatic.net/MjAxODA3MjZfODAg/MDAxNTMyNTkwMDA4Nzgx.SiIisnIOMuXGAFD3_Fc_a9-gKzkfsSur71_zzizvOvIg.GxHQHAlX-b9Cj1LLfOJCTS56nbrcy0hIJ2BoNuyHFkIg.PNG.ktw1332/12.png?type=w773" width="70%" height="70%"><br><br>
</div>
## Contact

Tae Un, Kang (ktw1332@korea.ac.kr)

## License

Automated CAN Analyzer is free software distributed under the Terms and Conditions of the CCL(Creative Commons License).

CC: SA-BY-NC

SA(Share-alike): Licensees may distribute derivative works only under a license identical ("not more restrictive") to the license that governs the original work.

BY(Attribution): Licensees may copy, distribute, display and perform the work and make derivative works and remixes based on it only if they give the author or licensor the credits (attribution) in the manner specified by these

NC(Non-commercial): Licensees may copy, distribute, display, and perform the work and make derivative works and remixes based on it only for non-commercial purposes.
