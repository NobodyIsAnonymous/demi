# DEMI

## Overview

DEMI is a smart contract governance proposal simulation and consistency checking tool.

## Main Features

### 1. Simulator
Use `execute_simulation_generator.py` to run smart contract governance proposal simulations.

```bash
python py_script/execute_simulation_generator.py
```

### 2. Consistency Check
Use `consistency_check.py` to detect description--execution mismatches in proposals.

```bash
python py_script/consistency_check.py
```

## File Descriptions

- `py_script/execute_simulation_generator.py` - Main simulator execution script
- `py_script/consistency_check.py` - Tool for detecting description--execution mismatch
- Other related Python scripts are located in the `py_script/` directory

## Usage

1. Ensure all required Python dependencies are installed
2. Run the simulator for governance proposal simulation
3. Use the consistency check tool to verify results
