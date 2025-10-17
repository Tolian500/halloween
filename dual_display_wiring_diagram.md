
### SHARED Connections (Both Displays)
```
Power & Data Lines:
┌─────────────┬─────────────┬─────────────┐
│ Connection  │ Pin Number  │ GPIO Number │
├─────────────┼─────────────┼─────────────┤
│ VCC         │ 1           │ 3.3V        │
│ GND         │ 6           │ GND         │
│ SDA / MOSI  │ 19          │ GPIO 10     │
│ SCL         │ 23          │ GPIO 11     │
└─────────────┴─────────────┴─────────────┘
```

### DISPLAY 1 (Left Eye) - Separate Connections
```
┌─────────────┬─────────────┬─────────────┐
│ Connection  │ Pin Number  │ GPIO Number │
├─────────────┼─────────────┼─────────────┤
│ CS          │ 24          │ GPIO 8      │
│ DC          │ 22          │ GPIO 25     │
│ RST         │ 13          │ GPIO 27     │
└─────────────┴─────────────┴─────────────┘
```

### DISPLAY 2 (Right Eye) - Separate Connections
```
┌─────────────┬─────────────┬─────────────┐
│ Connection  │ Pin Number  │ GPIO Number │
├─────────────┼─────────────┼─────────────┤
│ CS          │ 26          │ GPIO 7      │
│ DC          │ 18          │ GPIO 24     │
│ RST         │ 16          │ GPIO 23     │
└─────────────┴─────────────┴─────────────┘
```
