#include <AikoEvents.h> 
using namespace Aiko;

#define ver  "0.6.04-20100219"

// The following will be dependent on the Arduino in question. 
//    Need to implement ifdefs to cover them. (168, 328, Mega)

#define maxIO    13 
#define maxADC    6
#define maxPWM    6


//The following could be handled dynamically. 
#define Pin1 2
#define Pin2 3
#define Pin3 4
#define Pin4 5


#define Adc1 0 
#define Adc2 1
#define Adc3 2
#define Adc4 3

#define ledPin 13

#define pin8 8
#define pin9 9
#define pin10 10
#define pin11 11

//TODO This constant should be stored in eeprom and based on a uuid.
#define arduinoId "A6006AHI" 

int incomingByte=0;
char cmd[20];
byte numADC=0;
byte numIO=0;
byte usedADC=4;

byte pinAdc;

//char buf[20];

void init_ard()
{

  pinMode(ledPin, OUTPUT);
  
  pinMode(pin8, OUTPUT);
  pinMode(pin9, OUTPUT);
  pinMode(pin10, OUTPUT);
  pinMode(pin11, OUTPUT);

  digitalWrite(pin11,HIGH);
  delay(500);
  digitalWrite(pin11, LOW);
  Serial.println("(init)");
}

void setup()
{
  Serial.begin(38400);
  init_ard();

  //Serial.println("(ready)");
  //Events.addHandler(blinkLed,        200);
  Events.addHandler(serialHandler,   20);
  Events.addHandler(switchHandler,   25);
  //Events.addHandler(ledHandler,      100); //test purposes only...
  Events.addHandler(potHandler,      30);
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
    for (byte index = 0; index < count; index++) {
      char ch = Serial.read();
      //Serial.println(ch);
      if (ch == ';') {
        //Serial.println("(read jackpot)"); // DON'T JACKPOT IF BUFFER HAS OVERFLOWED !
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

void ledHandler() {
  static int state=LOW; 
  static int i=0;
  int lowled=8;
  int highled=11;

  if (i == 0) {
    i=lowled;
  }
  //for ( int i=8;i<=11;i++) {
  digitalWrite(i, state);  
  //}
  i++;
  if (i == highled+1) {
    i=lowled;
    state=!state;
  }
}

void potHandler() {
  //static int old_Adc1_val=1023; 
  //static int old_Adc2_val=1023;
  //static int old_Adc3_val=1023;
  //static int old_Adc4_val=1023;
  //static int old_Adc5_val=1023;
  //static int old_Adc6_val=1023;
  static byte jitter_offset=3;

  static int old_Adc_val[] ={1023, 1023, 1023, 1023, 1023, 1023};

  int adc_val;
  byte started_str;
  

  started_str=0;
  
  for(int i=0; i<4; i++) { // TODO:  Change the 4 to numAdc..
    adc_val=analogRead(i);
  
    if (adc_val < (old_Adc_val[i]-jitter_offset)  ||  adc_val > (old_Adc_val[i]+jitter_offset) ) {
      if (started_str==0)
      {
        Serial.print("(");
        Serial.print(arduinoId);
        Serial.print(" ");
      } 
      
      started_str=1;
      //Serial.print("DEBUG: old_Adc_val[1]: ");
      //Serial.println(old_Adc_val[1]);
      
      Serial.print("(adc");
      Serial.print((i+1));
      Serial.print(" ");
      Serial.print(adc_val+1);
      Serial.print(")");
      old_Adc_val[i]=adc_val;
    }
  } 
 
  if (started_str==1) {
    Serial.println(");");
  }
  
}

void switchHandler() {
  //static int pinvals[6];
  static int old_Pin1_val;
  static int old_Pin2_val;
  static int old_Pin3_val;
  int new_Pin1_val;
  int new_Pin2_val;
  int new_Pin3_val;
  byte started_str;

  new_Pin1_val=digitalRead(Pin1);
  new_Pin2_val=digitalRead(Pin2);
  new_Pin3_val=digitalRead(Pin3);

  /*Serial.print("DEBUG: old_Pin2_val: ");
   Serial.print(old_Pin2_val);
   Serial.print("new_Pin2_val: ");
   Serial.println(new_Pin2_val);
   */
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
      started_str=1;
      Serial.print("(");
      Serial.print(arduinoId);
      Serial.print(" ");
    }
    Serial.print("(pin2 ");
    Serial.print(old_Pin2_val);
    Serial.print(")");    
  }

  if (old_Pin3_val!= new_Pin3_val) {  
    old_Pin3_val=new_Pin3_val;
    if (started_str == 0) {
      started_str=1;
      Serial.print("(");
      Serial.print(arduinoId);
      Serial.print(" ");

    }
    Serial.print("(pin3 ");
    Serial.print(old_Pin3_val);
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
    Serial.print("(ver \"");
    Serial.print(ver);
    Serial.println("\");");
  }
  else if (strcmp(buf, "(numIO)") == 0 )
  {
    Serial.println("(debug mode: numIO");
    Serial.print("(numIO ");
    Serial.print(int(numIO));
    Serial.print(")");
  }  
  else if (strcmp(buf, "(pin8 1)") == 0 )
  {
    digitalWrite(pin8, 1);
  }
  else if (strcmp(buf, "(pin8 0)") == 0 )
  {
    digitalWrite(pin8, 0);
  }
  else if (strcmp(buf, "(pin9 1)") == 0 )
  {
    digitalWrite(pin9, 1);
  }
  else if (strcmp(buf, "(pin9 0)") == 0 )
  {
    digitalWrite(pin9, 0);
  }
  else if (strcmp(buf, "(pin10 1)") == 0 )
  {
    digitalWrite(pin10, 1);
  }
  else if (strcmp(buf, "(pin10 0)") == 0 )
  {
    digitalWrite(pin10, 0);
  }
  else if (strcmp(buf, "(pin11 1)") == 0 )
  {
    digitalWrite(pin11, 1);
  }
  else if (strcmp(buf, "(pin11 0)") == 0 )
  {
    digitalWrite(pin11, 0);
  } 
  else {
    Serial.println("(unknown command)");
  }
  
}

void loop() {
  Events.loop();
}


