#include <AikoEvents.h> 
using namespace Aiko;

#define ver     "0.3.01-20090929" 
byte ledPin =13;
byte Pin1=2;
byte Pin2=3;

int incomingByte=0;
char cmd[20];
//char buf[20];



void blinkLed() 
{
  //Serial.println("TEST");
  static int ledstate=HIGH;
  digitalWrite(ledPin, ledstate);
  ledstate= !ledstate;
}

void setup()
{
  Serial.begin(38400);
  pinMode(ledPin, OUTPUT);

  digitalWrite(ledPin,HIGH);


  delay(500);
  digitalWrite(ledPin,LOW);
  //Serial.println("(ready)");
  //Events.addHandler(blinkLed,      200);
  Events.addHandler(serialHandler,   20);
  Events.addHandler(switch2Handler,  100);
}

/*
* Arduino serial buffer is 128 characters.
 * At 115,200 baud (11,520 cps) the buffer is filled 90 times per second.
 * Need to run this handler every 10 milliseconds.
 */
void serialHandler() {
  static char buffer[10];
  static byte length = 0;
  static long timeOut = 0;

  unsigned long timeNow = millis();
  int count = Serial.available();


  if (count == 0) {
    if (length > 0) {
      if (timeNow > timeOut) {
        Serial.println("(time out error)");
        length = 0;
      }
    }
  }
  else 
  {
    /*Serial.print("(readCount ");
     Serial.print(count);
     Serial.println(")");
     */

    for (byte index = 0; index < count; index++) {
      char ch = Serial.read();
      //Serial.println(ch);
      if (ch == ';') {
        Serial.println("(read jackpot)"); // DON'T JACKPOT IF BUFFER HAS OVERFLOWED !
        buffer[length]=0;
        //Serial.println(buffer);
        processCommand(buffer);
        length = 0;
      }
      else 
      {
        if (length >= ((sizeof(buffer) / sizeof(*buffer))-1)) {
          Serial.println("(error overflow)");
        }
        else {
          buffer[length++] = ch;
        }
      }
    }

    timeOut = timeNow + 5000;
  }
}


void switchHandler() {
  static int old_Pin1_val;
  static int old_Pin2_val;
  int new_Pin1_val;
  int new_Pin2_val;


  new_Pin1_val=digitalRead(Pin1);
  new_Pin2_val=digitalRead(Pin2);

  if (old_Pin1_val!= new_Pin1_val) {
    old_Pin1_val=new_Pin1_val;

    Serial.print("(pin1=");
    Serial.print(old_Pin1_val);
    Serial.println(")");
  }

  if (old_Pin2_val!= new_Pin2_val) {  
    old_Pin2_val=new_Pin2_val;
    Serial.print("(pin2=");
    Serial.print(old_Pin2_val);

    Serial.println(")");    
  }
}

void processCommand(char *buf) {
  Serial.println(buf);
  if (strcmp(buf, "(ver)") == 0 )
  {
    Serial.print("(ver=");
    Serial.print(ver);
    Serial.println(")");
  } 
  else if (strcmp(buf, "(gear 1)") == 0 )
  {
    digitalWrite(ledPin,1);
  }
  else if (strcmp(buf, "(gear 0)") == 0 )
  {
    digitalWrite(ledPin,0);
  } 
  else {
    Serial.println("(unknown command)");
  }
}

void loop() {
  Events.loop();
}


