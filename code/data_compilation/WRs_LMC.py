import numpy as np
import pandas as pd
from uncertainties import ufloat


#SI:
G = 6.674E-11
Msun = 1.988E30
Rsun = 695700000.

auinRsun = 215.032

e = ufloat(0.0, 0.02)
P = ufloat(1.916, 0.0001)
K1 = ufloat(39., 7.)
K2 = ufloat(234., 14.)

C=1.0353 * 10**(-7) * P *(1 - e**2.)**(3./2.)
massfunction = P * 24. * 3600. * K1**3 * (1E3)**3 / 2 / np.pi / G * (1 - e**2)**(3./2.) / Msun    
q = K1/K2
print('Mass function:', massfunction)
print('mass ratio:', q)



#ddasd


## show *all* columns, no matter how many
#pd.set_option('display.max_columns', None)

## don’t wrap to multiple lines (try a large number or None to auto-detect)
#pd.set_option('display.width', None)

## make sure long cell contents (your [err-,val,err+] lists) are not truncated
#pd.set_option('display.max_colwidth', None)

## optionally, to keep the frame on one line rather than breaking it:
#pd.set_option('display.expand_frame_repr', False)

# now this will show every column in full:
from IPython.display import display


# Define columns, with key quantities stored as lists: [err-, value, err+]
columns = [
    "System Name", "RA", "Dec", "Period", "Eccentricity",
    "M1","M1_sin3i", "M2", "M2_sin3i", "q", "Mass Function",
    "Type1", "Type2", "Detection Method", "Reference", "Notes"
]

# Initialize empty DataFrame
observations_df = pd.DataFrame(columns=columns)

# Define helper function using [err-, value, err+] triplets
def add_observation(df, system_name,
                    ra, dec, period, ecc,
                    m1, m1_sin3i, m2, m2_sin3i, q, mass_func,
                    type1, type2, method, reference, notes=""):
    # use np.inf if it is a lower limit (0 if it is an upper limit)
    new_row = {
        "System Name": system_name,
        "RA": ra,                           # [err-, value, err+]
        "Dec": dec,                         # [err-, value, err+]

        "Period": period,                   # day [err-, value, err+]
        "Eccentricity": ecc,                # [err-, value, err+ ]

        "M1": m1,                           # Accretor star [err-, value, err+]
        "M1_sin3i": m1_sin3i,               # M1 sini^3 values [err-, value, err+] (= lower limit on m1)
        "M2": m2,                           # Donor (post MT 1) [err-, value, err+,]
        "M2_sin3i": m2_sin3i,               #  M2 sini^3 values [err-, value, err+] (= lower limit on m2)
        "q": q,                             # M2/M1 = donor/accretor [err-, value, err+, lower/upper limit? ]
        "Mass Function": mass_func,         # [err-, value, err+, lower/upper limit? ]
        "Type1": type1,                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        "Type2": type2,                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        "Detection Method": method,         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        "Reference": reference,             # ADS Bibcode    
        "Notes": notes
    }
    return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)



# BAT99 19
observations_df = add_observation(
        observations_df,
        'BAT99 19',
        [0.00001219, 77.418415, 0.00001219],                           # [err-, value, err+]
        [0.00000411, -68.890209, 0.00000411],                         # [err-, value, err+]
        [0.002, 17.994, 0.002],                   # day [err-, value, err+]
        [0.014, 0.020, 0.014],                # [err-, value, err+]
        [5, 40, 5],                           # Msun more massive component [err-, value, err+]
        [4.4, 39.6, 4.4],                           # Msun more massive component [err-, value, err+]
        [3, 22, 3],                           # Msun  less massive component [err-, value, err+]
        [2.6, 22.1, 2.6],                           # Msun more massive component [err-, value, err+]
        [0.026, 0.558, 0.026],                            #  between 0 and 1 [err-, value, err+]
         np.nan,         # Mass function
        'O6 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN4',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2003MNRAS.338.1025F', '2019A&A...627A.151S']  ,             # ADS Bibcode    
        ''
)

# BAT99 28
observations_df = add_observation(
        observations_df,
        'BAT99 28',
        [0.00002549, 79.818132, 0.00002549],                           # [err-, value, err+]
        [0.00001019, -69.655559, 0.00001019],                         # [err-, value, err+]
        [np.nan, 14.926, np.nan],                   # day [err-, value, err+]
        [0.05, 0.16, 0.05],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        [5.0, 29.5, 5.0],                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        [2.7, 10.2, 2.7],                           # Msun more massive component [err-, value, err+]
        [0.026, 0.558, 0.026],                            #  between 0 and 1 [err-, value, err+]
        np.nan,         # Mass function
        'O5 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WC6',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['1990ApJ...348..232M'],             # ADS Bibcode    
        ''
)

# BAT99 29
observations_df = add_observation(
        observations_df,
        'BAT99 29',
        [0.00010291, 80.186378, 0.00010291],                           # [err-, value, err+]
        [0.00004206, -65.472345, 0.00004206],                         # [err-, value, err+]
        [0.0003, 2.2016, 0.0003],                   # day [err-, value, err+]
        [0.13, 0.16, 0.13],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                            # between 0 and 1 [err-, value, err+]
        [0.019, 0.045, 0.019],         # Mass function
        'B1.5 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN3',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2003MNRAS.338.1025F']  ,             # ADS Bibcode    
        'Mass function computed with respect to M2'
)

# BAT99 38
observations_df = add_observation(
        observations_df,
        'BAT99 38',
        [0.00001938, 81.516516, 0.00001938],                           # [err-, value, err+]
        [0.00000772, -67.499191, 0.00000772],                         # [err-, value, err+]
        [np.nan, 3.03269, np.nan],                   # day [err-, value, err+]
        [np.nan, 0, np.nan],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                            # between 0 and 1 [err-, value, err+]
        [1.2, 6.5, 1.2],         # Mass function
        'O-uncertain',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WC4',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['1990ApJ...348..232M']  ,             # ADS Bibcode    
        'Mass function computed with respect to M2'
)

# BAT99 39
observations_df = add_observation(
        observations_df,
        'BAT99 39',
        [0.00004710, 81.626080, 0.00004710],                           # [err-, value, err+]
        [0.00001453, -68.840972, 0.00001453],                         # [err-, value, err+]
        [np.nan, 3.03269, np.nan],                   # day [err-, value, err+]
        [np.nan, 0, np.nan],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        [0.7, 3.5, 0.7],                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        [0.2, 0.6, 0.2],                           # Msun  less massive component [err-, value, err+]
        [0.032, 0.167, 0.032],                            # between 0 and 1 [err-, value, err+]
        np.nan,         # Mass function
        'O6 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WC4',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['1990ApJ...348..232M']  ,             # ADS Bibcode    
        ''
)



# BAT99 43
observations_df = add_observation(
        observations_df,
        'BAT99 43',
        [0.00001681, 81.907041, 0.00001681],                           # [err-, value, err+]
        [0.00000642, -70.601479, 0.00000642],                         # [err-, value, err+]
        [0.0002, 2.8160, 0.0002],                   # day [err-, value, err+]
        [0.05, 0.07, 0.05],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                            # between 0 and 1 [err-, value, err+]
        [0.7, 4.2, 0.7],         # Mass function
        'O9 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN3',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2003MNRAS.338.1025F']  ,             # ADS Bibcode    
        'Mass function computed with respect to M2'
)


# BAT99 49
observations_df = add_observation(
        observations_df,
        'BAT99 49',
        [0.00001740, 82.388363, 0.00001740],                           # [err-, value, err+]
        [0.00000647, -70.993011, 0.00000647],                         # [err-, value, err+]
        [0.03, 31.69, 0.03],                   # day [err-, value, err+]
        [0.11, 0.35, 0.011],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        [2.8, 6.8, 2.8],                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        [1.5, 3.4, 1.5],                           # Msun  less massive component [err-, value, err+]
        [0.12, 0.50, 0.12],                            # between 0 and 1 [err-, value, err+]
         np.nan,         # [err-, value, err+]
        'O9 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN4',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2003MNRAS.338.1025F']  ,             # ADS Bibcode    
        ''
)

# BAT99 59
observations_df = add_observation(
        observations_df,
        'BAT99 59',
        [0.00001333, 83.294044, 0.00001333],                           # [err-, value, err+]
        [0.00000536, -67.711959, 0.00000536],                         # [err-, value, err+]
        [0.0007, 4.7129, 0.0007],                   # day [err-, value, err+]
        [0.08, 0.32, 0.08],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                            # between 0 and 1 [err-, value, err+]
        [0.0035, 0.0112, 0.0035],         # [err-, value, err+]
        'O9 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN4',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2003MNRAS.338.1025F']  ,             # ADS Bibcode    
        'Mass function computed with respect to M2'
)


# BAT99 64
observations_df = add_observation(
        observations_df,
        'BAT99 64',
        [0.00001564, 83.747460, 0.00001564],                           # [err-, value, err+]
        [0.00000544, -69.735082, 0.00000544],                         # [err-, value, err+]
        [0.06, 37.59, 0.06],                   # day [err-, value, err+]
        [0.09, 0.16, 0.09],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,         #  between 0 and 1 [err-, value, err+]
        [0.18, 0.69, 0.18],                            # mass function
        'O9 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN4',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2003MNRAS.338.1025F']  ,             # ADS Bibcode    
        'Mass function computed with respect to M2'
)



# BAT99 71
observations_df = add_observation(
        observations_df,
        'BAT99 71',
        [0.02402164, 83.934496, 0.02402164],                           # [err-, value, err+]
        [0.00527778, -68.993553, 0.00527778],                         # [err-, value, err+]
        [0.0005, 2.3264, 0.0005],                   # day [err-, value, err+]
        [0.08, 0.09, 0.08],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,         #  between 0 and 1 [err-, value, err+]
        [1.5, 2.8, 1.5],                            # mass function
        'O6.5 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN3',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2003MNRAS.338.1025F']  ,             # ADS Bibcode    
        'Mass function computed with respect to M2'
)



# BAT99 77
observations_df = add_observation(
        observations_df,
        'BAT99 77',
        [0.00001658, 83.995307, 0.00001658],                           # [err-, value, err+]
        [0.00000578, -69.196622, 0.00000578],                         # [err-, value, err+]
        [0.00029, 3.00303, 0.00029],                   # day [err-, value, err+]
        [0.02, 0.32, 0.02],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        [5.1, 16.9, 5.1],                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        [3.4, 10.2, 3.4],                           # Msun  less massive component [err-, value, err+]
        [0.12, 0.60, 0.12],                            # between 0 and 1 [err-, value, err+]
         np.nan,         # [err-, value, err+]
        'O7.5 III',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN7',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2008MNRAS.389..806S', '2019A&A...627A.151S']  ,             # ADS Bibcode    
        'Mass function computed with respect to M2'
)


# BAT99 92
observations_df = add_observation(
        observations_df,
        'BAT99 92',
        [0.00001268, 84.454310, 0.00001268],                           # [err-, value, err+]
        [0.00000469, -69.085616, 0.00000469],                         # [err-, value, err+]
        [0.0006, 4.3125, 0.0006],                   # day [err-, value, err+]
        [0.02, 0.02, 0.02],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                            # between 0 and 1 [err-, value, err+]
        [0.28,3.79,0.28],         # [err-, value, err+]
        'O6 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN3',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2008MNRAS.389..806S']  ,             # ADS Bibcode    
        'Mass function computed with respect to M2'
)


# BAT99 103
observations_df = add_observation(
        observations_df,
        'BAT99 103',
        [0.00002304, 84.673418, 0.00002304],                           # [err-, value, err+]
        [0.00000719, -69.087553, 0.00000719],                         # [err-, value, err+]
        [0.00005, 2.75864, 0.00005],                   # day [err-, value, err+]
        [np.nan, 0., np.nan],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        [3.3, 12.3, 3.3],                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        [2.0, 6.4, 2.0],                           # Msun  less massive component [err-, value, err+]
        [0.09, 0.52, 0.09],                            # between 0 and 1 [err-, value, err+]
         np.nan,         # [err-, value, err+]
        'O4 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN5',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2019A&A...627A.151S']  ,             # ADS Bibcode    
        ''
)




# BAT99 126
observations_df = add_observation(
        observations_df,
        'BAT99 126',
        [0.00015947, 85.031394, 0.00015947],                           # [err-, value, err+]
        [0.00006089, -69.408865, 0.00006089],                         # [err-, value, err+]
        [0.04, 25.50, 0.04],                   # day [err-, value, err+]
        [0.06, 0.38, 0.06],                # [err-, value, err+]
        np.nan,                           # Msun more massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,                           # Msun  less massive component [err-, value, err+]
        np.nan,         #  between 0 and 1 [err-, value, err+]
        [0.011, 0.050, 0.011],                            # mass function
        'O7 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN3',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2003MNRAS.338.1025F']  ,             # ADS Bibcode    
        'Mass function computed with respect to M2'
)





# BAT99 129
observations_df = add_observation(
        observations_df,
        'BAT99 129',
        [0.00001563, 85.452374, 0.00001563],                           # [err-, value, err+]
        [0.00000492, -70.591885, 0.00000492],                         # [err-, value, err+]
        [0.0002, 2.7687, 0.0002],                   # day [err-, value, err+]
        [np.nan, 0, np.nan],                # [err-, value, err+]
        [6, 27, 14],                           # Msun more massive component [err-, value, err+]
        [2.4, 23.5, 2.4],                           # Msun  less massive component [err-, value, err+]
        [4, 16, 8],                           # Msun  less massive component [err-, value, err+]
        [1.5, 14.3, 1.5],                           # Msun  less massive component [err-, value, err+]
        [0.021, 0.611, 0.021],                            # between 0 and 1 [err-, value, err+]
         np.nan,         # [err-, value, err+]
        'O4 V',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'WR-WN5',                     # ["MS", "WD", "NS", "BH" "RG", "O", "B" ]
        'RV',         # list of strings ["Xray", "RV"= Radial velocity, "EB"=Eclipsing binary, "AB" = Astrometric binary, "Other"]  
        ['2006A%26A...447..667F']  ,             # ADS Bibcode    
        ''
)

print(observations_df['System Name'])
#0     BAT99 19
#1     BAT99 29
#2     BAT99 43
#3     BAT99 49
#4     BAT99 59
#5     BAT99 64
#6     BAT99 71
#7     BAT99 77
#8     BAT99 92
#9     BAT99 103
#10    BAT99 126
#11    BAT99 129

observations_df.to_pickle('WRs_LMC.pkl')

display(observations_df)

