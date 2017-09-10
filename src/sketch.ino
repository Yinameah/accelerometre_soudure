/*
 ADXL362_SimpleRead.ino -  Simple XYZ axis reading example
 for Analog Devices ADXL362 - Micropower 3-axis accelerometer
 go to http://www.analog.com/ADXL362 for datasheet
 
 
 License: CC BY-SA 3.0: Creative Commons Share-alike 3.0. Feel free 
 to use and abuse this code however you'd like. If you find it useful
 please attribute, and SHARE-ALIKE!
 
 Created June 2012
 by Anne Mahaffey - hosted on http://annem.github.com/ADXL362

 Modified May 2013
 by Jonathan Ruiz de Garibay
 
Connect SCLK, MISO, MOSI, and CSB of ADXL362 to
SCLK, MISO, MOSI, and DP 10 of Arduino 
(check http://arduino.cc/en/Reference/SPI for details)
 
*/ 

#define LED_G 7
#define LED_R 6

#define nbr_sample 200

#include <SPI.h>
#include <ADXL362.h>

ADXL362 xl;
int16_t xdata, ydata, zdata, tdata;
int16_t zdata_buffer;
int16_t bunch_z[nbr_sample];
unsigned long bunch_milli[nbr_sample];
int i_bunch = 0;


int incomingByte;
bool transmission_has_end = true;
bool led_r_on = false;
bool led_g_on = false;

byte read_reg_value;


void setup(){
  
  Serial.begin(115200);
  delay(500);
  Serial.println("MSG : Serial up and running");
  Serial.println("MSG : Will send millis:X:Y:Z:Temp");

  // Begin SPI for accel (pin 5)
  xl.begin(5);
  xl.beginMeasure();

  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);


  // à vérifier, high power normalement
  xl.SPIwriteOneRegister(0x2D, 0x32);

  // Filter Register Control (8g mode)
  xl.SPIwriteOneRegister(0x2C, 0xD7);

  // laisse initialiser, mec !
  delay(100);
}

void loop(){

    // 44 micros seconds pour cette lecture (apparement)
    xl.readXYZTData(xdata, ydata, zdata, tdata);

    // 760 micros seconds pour cette série d'infos (115200 bauds)
    //Serial.print('#');
    Serial.print(millis());
    Serial.print(":");
    Serial.print(xdata);	 
    Serial.print(":");
    Serial.print(ydata);	 
    Serial.print(":");
    Serial.print(zdata);	 
    Serial.print(":");
    Serial.println(tdata);	 

    // 400 Hz (res acceleromètre) => 2500 - 44 - 760 = 1696
    delayMicroseconds(1700);


  if(Serial.available() > 1){
    incomingByte = Serial.read();

    if (incomingByte == 97){
      led_r_on = !led_r_on;

        read_reg_value = xl.SPIreadOneRegister(0x2D);

        Serial.print("Value of reg 0x2D (HEX): ");
        Serial.println(read_reg_value, HEX);

    }
    else if (incomingByte == 98){
      led_g_on = !led_g_on;

        read_reg_value = xl.SPIreadOneRegister(0x2D);

        Serial.print("Value of reg 0x2D (HEX): ");
        Serial.println(read_reg_value, HEX);
    }
  }
    
    //update_led();  
}

void update_led(){
  if (led_g_on) {
    digitalWrite(LED_G, HIGH);
  } else {
    digitalWrite(LED_G, LOW);
  }
  if (led_r_on) {
    digitalWrite(LED_R, HIGH);
  } else {
    digitalWrite(LED_R, LOW);
  }
}
    
