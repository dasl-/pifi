#include "FastLED.h"

#define ROWS 6
#define COLS 30
constexpr uint8_t DATA_PIN[] = {2,4,6,8,10,12};
constexpr uint8_t CLOCK_PIN[] = {3,5,7,9,11,13};
CRGB leds[ROWS][COLS];

// note, we need ~12 characters per LED right now, 1000 allows for ~80 leds 
// ~3char/led
const unsigned int MAX_INPUT = 1000;

void setup () {
  // LED Output
  FastLED.addLeds<APA102, DATA_PIN[0], CLOCK_PIN[0]>(leds[0], COLS);
  FastLED.addLeds<APA102, DATA_PIN[1], CLOCK_PIN[1]>(leds[1], COLS);
  FastLED.addLeds<APA102, DATA_PIN[2], CLOCK_PIN[2]>(leds[2], COLS);
  FastLED.addLeds<APA102, DATA_PIN[3], CLOCK_PIN[3]>(leds[3], COLS);
  FastLED.addLeds<APA102, DATA_PIN[4], CLOCK_PIN[4]>(leds[4], COLS);
  FastLED.addLeds<APA102, DATA_PIN[5], CLOCK_PIN[5]>(leds[5], COLS);
  
  LEDS.setBrightness(50);

  // Serial Input
  Serial.begin (115200);
  Serial.setTimeout(5);

  Serial.println("READY");
}

void process_data (char * data) {
  Serial.println("data");
  Serial.println(data);
//  old code for x,y:rrr,ggg,bbb
//  char *end_str;
//  char *token = strtok_r(data, "&", &end_str);
//  while (token != NULL) {
//      char *end_token;
//      char *token2 = strtok_r(token, ",", &end_token);
//      byte commands[5];
//      byte command_i = 0;
//      while (token2 != NULL) {
//          commands[command_i] = atoi(token2);
//          command_i++;
//          token2 = strtok_r(NULL, ",", &end_token);
//      }
//      setPixel(commands[0], commands[1], commands[2], commands[3], commands[4]);
//      token = strtok_r(NULL, "&", &end_str);
//  }
//  FastLED.show();

  // format: x:bbb&bbb&bbb&...
  char *end_str;
  char *token = strtok_r(data, ":", &end_str);
  while (token != NULL) {
      char *end_token;
      char *token2 = strtok_r(token, "&", &end_token);
      byte brightness[COLS];
      byte brightness_i = 0;
      while (token2 != NULL) {
          brightness[brightness_i] = atoi(token2);
          brightness_i++;
          token2 = strtok_r(NULL, "&", &end_token);
      }
      setPixels(atoi(token), brightness);
      token = strtok_r(NULL, ":", &end_str);
  }
}
  
void processIncomingByte (const byte inByte)
  {
  static char input_line [MAX_INPUT];
  static unsigned int input_pos = 0;

  switch (inByte) {
    case '\n':   // end of text
      input_line[input_pos] = 0;  // terminating null byte
      
      // terminator reached! process input_line here ...
      process_data(input_line);
      
      // reset buffer for next time
      input_pos = 0;  
      break;

    case '\r':
      break;

    default:
      // keep adding if not full ... allow for terminating null byte
      if (input_pos < (MAX_INPUT - 1))
        input_line [input_pos++] = inByte;
      break;

  }
}

void setPixels(byte row, byte * brightness) {
  Serial.println("set pixels");
  Serial.print(row);
  Serial.print(":");
  for (int i = 0; i < COLS; i++) {
    Serial.print(brightness[i]);
    Serial.print("&");
    leds[row][i].setRGB(brightness[i],brightness[i],brightness[i]);
  }
  Serial.println(";");
  FastLED.show();
}

void loop() {
  while (Serial.available () > 0) {
    processIncomingByte (Serial.read());
  }
}
