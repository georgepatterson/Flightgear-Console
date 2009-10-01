#include <AikoEvents.h> 
using namespace Aiko;

#define ver  "0.4.01-20090927" 

#define Pin1 2
#define Pin2 3

#define Adc1 0 
#define Adc2 1

#define ledPin 13
#define arduinoId "A6006AHI"

int incomingByte=0;
char cmd[20];
//char buf[20];

void init_ard()
{
  pinMode(ledPin, OUTPUT);

  digitalWrite(ledPin,HIGH);

  delay(500);
  digitalWrite(ledPin, LOW);
  Serial.println("(init)");
}

void setup()
{
  init_ard();
  Serial.begin(38400);

  //Serial.println("(ready)");
  //Events.addHandler(blinkLed,      200);
  Events.addHandler(serialHandler,   20);
  Events.addHandler(switchHandler,  25);
  Events.addHandler(potHandler,  30);
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

void potHandler() {
  static int old_Adc1_val=1023; 
  static int old_Adc2_val=1023;
  static byte jitter_offset=2;
  //define jitter_offset 2

    int new_Adc1_val;
  int new_Adc2_val;
  byte started_str;

  new_Adc1_val=analogRead(Adc1);
  new_Adc2_val=analogRead(Adc2);
  //Serial.println(new_Adc1_val);

  started_str=0;
  if (new_Adc1_val < (old_Adc1_val-jitter_offset)  ||  new_Adc1_val > (old_Adc1_val+jitter_offset) ) {
    started_str=1;
    old_Adc1_val=new_Adc1_val;

    Serial.print("(");
    Serial.print(arduinoId);
    Serial.print(" ");
    Serial.print("(adc1 ");
    Serial.print(new_Adc1_val);
    Serial.print(")");
    //delay(500);
  }

  // Debug the first one...
  //if (old_Adc2_val!= new_Adc2_val) {
  if (new_Adc2_val < (old_Adc2_val-jitter_offset)  ||  new_Adc2_val > (old_Adc2_val+jitter_offset) ) {
    old_Adc2_val=new_Adc2_val;
    if (started_str==0)
    {
      Serial.print("(");
      Serial.print(arduinoId);
      Serial.print(" ");
    } 
    started_str=1;
    Serial.print("(adc2 ");
    Serial.print(new_Adc2_val);
    Serial.print(")");
  }

  if (started_str==1) {
    Serial.println(");");
  }


}

void switchHandler() {
  static int old_Pin1_val;
  static int old_Pin2_val;
  int new_Pin1_val;
  int new_Pin2_val;
  byte started_str;

  new_Pin1_val=digitalRead(Pin1);
  new_Pin2_val=digitalRead(Pin2);

  started_str=0;
  if (old_Pin1_val!= new_Pin1_val) {
    old_Pin1_val=new_Pin1_val;
    started_str=1;
    Serial.print("(");
    Serial.print(arduinoId);
    Serial.print(" ");
    Serial.print("(pin1 ");
    Serial.print(old_Pin1_val);
    Serial.print(")");
  }

  if (old_Pin2_val!= new_Pin2_val) {  
    old_Pin2_val=new_Pin2_val;
    if (started_str == 0) {
      Serial.print("(");
      Serial.print(arduinoId);
      Serial.print(" ");
    
      started_str=1;
    }
    Serial.print("(pin2 ");
    Serial.print(old_Pin2_val);
    Serial.print(")");    
  }
  if (started_str==1) {
    Serial.println(");");
  }
  //Serial.print(")");
}

void processCommand(char *buf) {
  //Serial.println(buf);

  if (strcmp(buf, "(init)") == 0 )
  {
    init_ard();
  } 
  else if (strcmp(buf, "(ver)") == 0 )
  {
    Serial.print("(ver ");
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





