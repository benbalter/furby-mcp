# Furby Connect Action Reference

This document provides information about Furby Connect actions that can be triggered using the `do_action` tool.

## Action Structure

Furby actions are defined by four parameters:
- **input**: Where to find the action (typically 0 for built-in actions)
- **index**: The main action category
- **subindex**: Sub-category within the action
- **specific**: Specific variant of the action

## Common Actions

Based on the bluefluff reverse engineering project, here are some common Furby actions:

### Basic Movements
- **Yawn**: `input=0, index=0, subindex=0, specific=0`
- **Sneeze**: `input=0, index=1, subindex=0, specific=0`
- **Giggle**: `input=0, index=2, subindex=0, specific=0`
- **Sing**: `input=0, index=3, subindex=0, specific=0`

### Reactions
- **Happy**: `input=0, index=4, subindex=0, specific=0`
- **Sad**: `input=0, index=5, subindex=0, specific=0`
- **Excited**: `input=0, index=6, subindex=0, specific=0`
- **Scared**: `input=0, index=7, subindex=0, specific=0`

### Speech
- **Greeting**: `input=0, index=10, subindex=0, specific=0`
- **Question**: `input=0, index=11, subindex=0, specific=0`
- **Answer**: `input=0, index=12, subindex=0, specific=0`

## Action Discovery

Furby Connect has thousands of different action sequences. To discover more actions:

1. Check the [bluefluff action documentation](https://github.com/Jeija/bluefluff/blob/master/doc/actions.md)
2. Use the debug screen feature to see internal action IDs
3. Experiment with different parameter combinations

## Notes

- Actions may vary depending on Furby's current mood and state
- Some actions are context-dependent (e.g., only trigger when Furby is tired)
- The antenna joystick and sensors can influence which actions are available
- Some actions are part of DLC (downloadable content) updates

## Mood System

Furby's behavior is influenced by five mood parameters (0-100):
- **Excited**: How energetic Furby is
- **Displeased**: How unhappy Furby is
- **Tired**: How sleepy Furby is
- **Fullness**: How full/hungry Furby is
- **Wellness**: Overall health/happiness

These can be adjusted using the `set_mood` tool to influence which actions Furby will perform.

## Further Reading

For more detailed information about Furby Connect's internal workings:
- [Bluefluff Documentation](https://github.com/Jeija/bluefluff/tree/master/doc)
- [Bluetooth Protocol](https://github.com/Jeija/bluefluff/blob/master/doc/bluetooth.md)
- [GeneralPlus Commands](https://github.com/Jeija/bluefluff/blob/master/doc/generalplus.md)
