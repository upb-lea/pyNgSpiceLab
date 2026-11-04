# NG-Spice toolbox

## Requirements

- Following initialisation APIs shall be available
    - Init toolbox with circuit path
    - Set components, where the parameter (value or model) shall be changed
    - These components are passive components (L, C, R)
    - Active components (Q-Model, Diode model)
    - Signal sources like pulse sources (New)
    - The initialisation value shall be validated  
      (Eg. exists are the components defined as changed within the circuit)


- General APIs to read out the initialisation shall be available
    - Read out the components, which are available within the given circuit  
      (Names and current setting of the initialized circuit. Background:  These  names shall be used to change the parameters and
       to get current results 
       Question: Base current of FET needs more, than the FET component name. Maybe a filtered output like which current can be measured?)
    - Read out the net names
      (Names of the net. Background:  These  names shall be used to access the results (Voltage...))

- To control the simlation following APIs shall be available  
    - Set a fixed runtime or (optional) a trigger condition to stop the simulation (within the given runtime)
    - Start the simulation with the list of values/models of previously assigned components to change.
    - Set following parameter, passed through the ng-spice simulation
        - ng-spice simulation step with (dynamic or fix)
        - pre-simulation time of ng-spice
        - other parameter (provide a list of parameters to decide, which parameters makes sense to pass through)


- Access to results
    - After simulation the results shall be available to read out  
        - Current and voltages waveform of a given simulation time range shall be availble
        - Signal combination of a given simulation time range shall be availble  
          (E.g. Power as U*I)
    - The waveforms shall be stored in a pysignalscope compatible format so that this tool can be used to display the waveformes

- Definition of a complex trigger condition
    - The trigger condition shall consider
        - Signals (e.g. exceed a threshold)
        - Combination of signals of the last time range (U*I for power loss, engergy) or RMS  
          peak-to peak value of signals (e.g. u1max-u2min>threshold) 
          ( indentify the suitable API for this approach)

    - The trigger condition shall consider signals (e.g. exceed a threshold)


### Results

A example could be geckocircuit 2

