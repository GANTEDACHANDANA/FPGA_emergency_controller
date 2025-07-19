<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

How it works
This project implements a safety-critical Emergency Stop Device (ESD) controller with integrated watchdog timer functionality. The system is designed for industrial applications where machine safety is paramount.

Key Components:
Dual Emergency Stop Inputs: The controller monitors two independent E-STOP buttons (ESTOP_A_N and ESTOP_B_N), both active-low. If either button is pressed, the system immediately enters shutdown mode.

Button Debouncing: All input buttons use hardware debouncing with a 20-bit counter to eliminate mechanical switch bounce and ensure reliable operation.

Watchdog Timer: A 500ms watchdog timer continuously monitors for "kick" signals (WDG_KICK input). If no kick is received within the timeout period, the system assumes a fault condition and triggers shutdown.

State Machine: The core safety logic uses a three-state finite state machine:

RUN: Normal operation mode
SHUTDOWN: Safety shutdown active
WAIT_ACK: Waiting for operator acknowledgment after fault clearance
Status Indication: The LED_STATUS output provides visual feedback:

Solid ON: Fault condition (E-STOP pressed or watchdog timeout)
Blinking (0.5Hz): Normal operation
Safety Features:
Safe startup: System begins in SHUTDOWN state on reset
Fault latching: Once a fault occurs, it must be explicitly acknowledged
Redundant inputs: Either E-STOP button can trigger shutdown
Watchdog protection: Automatic shutdown if control system becomes unresponsive
How to test
Basic Functionality Test:
Power-up Test: After reset, verify SHUTDOWN output is HIGH and LED_STATUS is solid ON (safe startup state)
Acknowledge Test:
Press and release ACK_N button (ui[2])
SHUTDOWN should remain HIGH
LED_STATUS should start blinking (normal operation)
Emergency Stop Test:
Press either ESTOP_A_N (ui[0]) or ESTOP_B_N (ui[1])
SHUTDOWN should immediately go HIGH
LED_STATUS should become solid ON
Release E-STOP button
Press and release ACK_N to clear fault
System should return to blinking LED mode
Watchdog Test:
Ensure system is in RUN mode (LED blinking)
Stop sending WDG_KICK pulses (ui[3])
After 500ms, SHUTDOWN should go HIGH and LED should become solid
Send ACK_N pulse to clear fault
Recommended Test Sequence:
1. Apply reset (rst_n = 0, then 1)
2. Verify SHUTDOWN = 1, LED_STATUS = 1
3. Send ACK pulse → LED should start blinking
4. Send periodic WDG_KICK pulses (every 100-400ms)
5. Test E-STOP A: press ui[0] → verify shutdown
6. Release ui[0], send ACK → verify recovery
7. Test E-STOP B: press ui[1] → verify shutdown  
8. Release ui[1], send ACK → verify recovery
9. Stop WDG_KICK for >500ms → verify watchdog timeout
10. Send ACK → verify recovery
Timing Requirements:
Clock frequency: 50 MHz (as configured)
Watchdog timeout: 500ms
LED blink rate: 0.5Hz (1-second period)
Debounce time: ~42ms (with 20-bit counter at 50MHz)
External hardware
Required Hardware:
Emergency Stop Buttons (2x):

Industrial-grade emergency stop buttons (mushroom head type recommended)
Normally-closed (NC) contacts
Connect between ui[0]/ui[1] and ground
When pressed, input goes LOW (active-low operation)
Acknowledge Button (1x):

Momentary push button (normally open)
Connect between ui[2] and ground with pull-up resistor
Used to acknowledge faults and reset the system
Status LED:

Standard LED with appropriate current-limiting resistor
Connect to uo[1] (LED_STATUS output)
Indicates system status (solid = fault, blinking = normal)
Watchdog Kick Source:

Connect ui[3] to your main control system
Should provide periodic pulses (every 100-400ms recommended)
Can be driven by microcontroller, PLC, or other control system
Optional Hardware:
Shutdown Output Load:

Connect uo[0] (SHUTDOWN) to your machine's safety relay or contactor
May require additional driver circuitry depending on load requirements
Consider using optoisolation for electrical safety
Pull-up Resistors:

10kΩ pull-up resistors recommended for all button inputs
Ensures proper HIGH levels when buttons are not pressed
Connection Diagram:
E-STOP A ----[NC]---- ui[0] ----[10kΩ]---- VCC
E-STOP B ----[NC]---- ui[1] ----[10kΩ]---- VCC  
ACK BTN  ----[NO]---- ui[2] ----[10kΩ]---- VCC
MCU/PLC  ------------- ui[3]
                       
LED ------[Resistor]-- uo[0] (LED_STATUS)
Relay Driver --------- uo[1] (SHUTDOWN)
Safety Note: This controller is designed for educational/demonstration purposes. For actual industrial safety applications, ensure compliance with relevant safety standards (ISO 13849, IEC 62061, etc.) and consider additional safety measures such as redundant processors, safety-rated components, and proper certification.

