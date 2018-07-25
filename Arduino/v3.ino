#include <SPI.h>
#include <Arduino.h>
#include "mcp_can.h"
const int SPI_CS_PIN = 9;
MCP_CAN CAN(SPI_CS_PIN);
bool token=false;
bool token2=false;
char inChar;
int i=0;
int index=0;
unsigned char len = 0;
short canId2;
unsigned char ATTACK_MESSAGE[10] = {0,0,0,0,0,0,0,0,0,0};
int ATTACK_MESSAGE_i=0;
int k=0;
void setup(){
  pinMode(13, OUTPUT);
  digitalWrite(13,HIGH);
  digitalWrite(13,LOW);
  Serial.begin(250000);
  Serial.flush();
  while (CAN_OK != CAN.begin(CAN_500KBPS));
}
void loop(){
  i=0;
  if (token == false) 
    return;
  len = 0;
  byte buf[8];
  short canId;
  if (CAN_MSGAVAIL == CAN.checkReceive())           // check if data coming
  {
    CAN.readMsgBuf(&len, buf);    // read data,  len: data length, buf: data buf
    canId = CAN.getCanId();    
    Serial.write(byte(len));    
    Serial.write(byte((canId >> 8) & 0xFF));    
    Serial.write(byte(canId & 0xFF));
    while(i<len) // print the data
    {
      Serial.write(byte(buf[i]));
      i=i+1;
    }
  }
}    
void serialEvent() {
    if(Serial.available()>0){
      inChar = Serial.read();                
      if(token2==true){
        if(k>10 || (byte(inChar)!=0 && byte(inChar)!=254) ){
          ATTACK_MESSAGE[ATTACK_MESSAGE_i] = byte(inChar);
          ATTACK_MESSAGE_i=ATTACK_MESSAGE_i+1;        
          if(ATTACK_MESSAGE_i==10){
            Serial.write(ATTACK_MESSAGE,10);
            ATTACK_MESSAGE_i=0;
            unsigned char stmp2[8] = {0,0,0,0,0,0,0,0};
            for(int i=2;i<10;i++){
              stmp2[i-2]=ATTACK_MESSAGE[i];
            }
            CAN.sendMsgBuf(ATTACK_MESSAGE[0]*100+ATTACK_MESSAGE[1], 0, 8, stmp2);
          }
        }
        k=k+1;
      }
      else if (byte(inChar) == 255 && token2==false) {      
        for(int j=0;j<100;j++){
          Serial.write(byte(0xff));
        }
        token = (token != true);
      }
      else if(byte(inChar) == 254){
          k=0;
          for(int i=0;i<10;i++)
             ATTACK_MESSAGE[i]=0;         
          token2 = (token2 != true);
      }
      else if(token2==false){             
        unsigned char a[8] = {0x02,0x01,inChar,0x00,0x00,0x00,0x00,0x00};
        CAN.sendMsgBuf(0x7DF, 0, 8, a);
      }
    }    
}
