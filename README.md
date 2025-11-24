# Setup
1. Install Python >= 3.14.8
2. Create and activate a virtual environment:

   For **Linux** OG's and **Mac**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
   
   For **Windows** users:
   ```bash
   python -m venv venv
   venv/scripts/activate # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:

   For **Linux** OG's and **Mac**:
   ```bash
   pip install -r requirements.txt
    ```
   
   For **Windows** users:
   ```bash
   python -m pip install -r requirements.txt
    ```

# Usage
To run the application, use the following command:
```bash
python main.py -f <path_to_your_gpx
```

# DISCLAIMER
The elapsed time shown in the output is the **Calculation time for the lookup**. As the script is server oriented,
all the preprocessing ahead of time is not included in the elapsed time shown, since it can be performed once at
startup.