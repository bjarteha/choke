import re  # regex
import numpy as np
from scipy import interpolate

def extract_int_from_string(line):
    numbers = [int(num_str) for num_str in re.findall(r'\b\d+\b', line)]
    return numbers


def extract_float_from_string(line):
    numbers = [float(num_str) for num_str in re.findall("[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", line)]
    return numbers


class PhysicalProperty:
    def __init__(self):
        self.data = []
        self.description = 'unspecified'
        self.unit = 'unspecified'

    def set_data(self, data):
        self.data = data

    def set_description(self, description):
        self.description = description

    def set_unit(self, unit):
        self.unit = unit


# The following dictionary defines the olga tab fluid properties. The dictionary gives a mapping between the class
# member variable and the corresponding key-word found in an Olga tab file
olga_tab_parameters = {"WATER_OPTION": "WATER-OPTION", "ENTROPY": "ENTROPY", "NONEQ": "NONEQ"}

# The following double dictionary defines the physical properties specified in an Olga tab file. The dictionary
# key-words correspond to physical properties in the OlgaPvt class
olga_tab_properties = {"ROGTB": {"search": "GAS DENSITY", "description": "Gas densities"},
                       "ROOTB": {"search": "LIQUID DENSITY", "description": "Oil densities"},
                       "ROWTB": {"search": "WATER DENSITY", "description": "Water densities"},
                       "DRGPTB": {"search": "PRES. DERIV. OF GAS DENS.", "description": "Partial derivatives of gas "
                                                                                        "densities with respect to "
                                                                                        "pressure"},
                       "DROPTB": {"search": "PRES. DERIV. OF LIQUID DENS.", "description": "Partial derivatives of oil "
                                                                                           "densities with respect to "
                                                                                           "pressure"},
                       "DRWPTB": {"search": "PRES. DERIV. OF WATER DENS.",
                                  "description": "Partial derivatives of water "
                                                 "densities with respect to "
                                                 "pressure"},
                       "DRGTTB": {"search": "TEMP. DERIV. OF GAS DENS.", "description": "Partial derivatives of gas "
                                                                                        "densities with respect to "
                                                                                        "temperature"},
                       "DROTTB": {"search": "TEMP. DERIV. OF LIQUID DENS.", "description": "Partial derivatives of oil "
                                                                                           "densities with respect to "
                                                                                           "temperature"},
                       "DRWTTB": {"search": "TEMP. DERIV. OF WATER DENS.",
                                  "description": "Partial derivatives of water "
                                                 "densities with respect to "
                                                 "temperature"},
                       "RSGTB": {"search": "GAS MASS FRACTION OF GAS . OIL", "description": "Gas mass fraction in gas "
                                                                                            "and oil mixture; the gas "
                                                                                            "mass divided by the gas and "
                                                                                            "oil mass"},
                       "RSWTB": {"search": "WATER MASS FRACTION OF GAS", "description": "Water vapour mass fraction in "
                                                                                        "the gas phase"},
                       "VSGTB": {"search": "GAS VISCOSITY", "description": "Dynamic viscosity for gas"},
                       "VSOTB": {"search": "LIQ. VISCOSITY", "description": "Dynamic viscosity for oil"},
                       "VSWTB": {"search": "WAT. VISCOSITY", "description": "Dynamic viscosity for water"},
                       "CPGTB": {"search": "GAS SPECIFIC HEAT",
                                 "description": "Gas heat capacity at constant pressure"},
                       "CPOTB": {"search": "LIQ. SPECIFIC HEAT",
                                 "description": "Oil heat capacity at constant pressure"},
                       "CPWTB": {"search": "WAT. SPECIFIC HEAT",
                                 "description": "Water heat capacity at constant pressure"},
                       "HGTB": {"search": "GAS ENTHALPY", "description": "Gas enthalpy"},
                       "HOTB": {"search": "LIQ. ENTHALPY", "description": "Oil enthalpy"},
                       "HWTB": {"search": "WAT. ENTHALPY", "description": "Water enthalpy"},
                       "TKGTB": {"search": "GAS THERMAL COND.", "description": "Gas thermal conductivity"},
                       "TKOTB": {"search": "LIQ. THERMAL COND.", "description": "Oil thermal conductivity"},
                       "TKWTB": {"search": "WAT. THERMAL COND.", "description": "Water thermal conductivity"},
                       "SIGOGT": {"search": "SURFACE TENSION GAS/OIL",
                                  "description": "Surface tension between gas and oil"},
                       "SIGWGT": {"search": "SURFACE TENSION GAS/WATER",
                                  "description": "Surface tension between gas and "
                                                 "water"},
                       "SIGWOT": {"search": "SURFACE TENSION WATER/OIL", "description": "Surface tension between water "
                                                                                        "and oil"},
                       "SGTB": {"search": "GAS ENTROPY", "description": "Gas specific entropy"},
                       "SOTB": {"search": "LIQUID ENTROPY", "description": "Oil specific entropy"},
                       "SWTB": {"search": "WATER ENTROPY", "description": "Water specific entropy"}}


class OlgaPvt:
    def __init__(self, pvt_file):
        self.file = pvt_file
        self.EOS = 'unspecified'
        self.fluid_name = 'unspecified'
        self.N = 0
        self.NTABP = 0
        self.NTABT = 0
        self.RSWTOTB = 0
        self.PP = []
        self.TT = []
        self.PBB = []
        self.PDEW = []
        for param in olga_tab_parameters:
            exec(f"self.{param} = False")

        for entity in olga_tab_properties:
            exec(f"self.{entity} = PhysicalProperty()")

    def __str__(self):
        return f"{self.file}"

    def read_pvt(self):
        fid_pvt = open(self.file, 'r')
        while True:
            input_line = fid_pvt.readline()
            if not input_line:
                break

            s = input_line.strip()
            # Check for FLUIDF (any number of characters encapsulated in apostrophes)
            match = re.search("'.*'", s)
            if match:
                self.read_fluidf(input_line, fid_pvt)
                continue  # read new line from top of outer while loop

            found = False
            for entity in olga_tab_properties:
                search_str = olga_tab_properties[entity]["search"]
                match = re.search(search_str, s)
                if match:
                    # get rid of search match from string
                    s = ''.join(re.split(search_str, s))
                    exec(f"self.{entity}.set_unit('{s.strip()}')")
                    tmp = self.read_physical_properties(fid_pvt)
                    exec(f"self.{entity}.set_data(tmp)")
                    description = olga_tab_properties[entity]["description"]
                    exec(f"self.{entity}.set_description('{description}')")
                    found = True
                    break  # jump out of for loop

            if found:
                continue  # read new line from top of outer while loop

        fid_pvt.close()

    def read_physical_properties(self, fid_pvt):
        num_data = self.NTABT * self.NTABP  # number of floats to expect
        num_so_far = 0
        tmp = np.zeros(num_data)
        while num_so_far < num_data:
            line = fid_pvt.readline()
            ss = extract_float_from_string(line)
            n = len(ss)
            tmp[num_so_far:num_so_far + n] = ss[0:n]
            num_so_far += n

        # store data into 2 - dimensional array - fill column by column fortran style
        data = np.reshape(tmp, (self.NTABT, self.NTABP), order='F')
        return data

    def read_fluidf(self, line, fid_pvt):
        line = line.replace("'", "")
        line = line.replace(",", " ")

        for param in olga_tab_parameters:
            search_str = olga_tab_parameters[param]
            match = re.search(search_str, line)
            if match:
                exec(f"self.{param} = True")
                # get rid of search match from string
                line = ''.join(re.split(search_str, line))

        search_str = '(EOS=)([^}]*)'
        match = re.search(search_str, line)
        if match:
            tmp = ''.join(re.split('EOS=', match[0]))
            tmp = tmp.strip()
            if len(tmp) == 0:
                self.EOS = 'UNKNOWN'
            else:
                self.EOS = tmp
            line = ''.join(re.split(match[0], line))
        else:
            self.EOS = 'UNKNOWN'

        self.fluid_name = line.strip()

        # first line after shall contains grid size info
        line = fid_pvt.readline()
        ss = extract_float_from_string(line)
        self.NTABP = int(ss[0])
        self.NTABT = int(ss[1])

        # Total water mass fraction for the feed. Optionally, default value = 0
        # (Only used together with three-phase tables)
        self.RSWTOTB = ss[2]  # do not know what type of parameter this is

        self.PP = np.zeros(self.NTABP)
        self.TT = np.zeros(self.NTABT)
        self.PBB = np.zeros(self.NTABT)
        self.PDEW = np.zeros(self.NTABT)

        # the lines following shall contain table data
        self.N = self.NTABP + 3 * self.NTABT  # number of floats to expect
        num_floats = 0
        data = np.zeros(self.N)
        while num_floats < self.N:
            line = fid_pvt.readline()
            ss = extract_float_from_string(line)
            n = len(ss)
            data[num_floats:num_floats + n] = ss[0:n]
            num_floats += n

        self.PP = data[0:self.NTABP]
        self.TT = data[self.NTABP:self.NTABP + self.NTABT]
        self.PBB = data[self.NTABP + self.NTABT:self.NTABP + 2 * self.NTABT]
        self.PDEW = data[self.NTABP + 2 * self.NTABT:self.NTABP + 3 * self.NTABT]

    # Main function for 2-interpolation of Olga data tables
    def lookup_olga_table(self, pressure, temperature, data_table):
        # f = interpolate.interp2d(self.PP, self.TT, data_table, kind='cubic', bounds_error=False)
        f = interpolate.RectBivariateSpline(self.PP, self.TT, data_table)
        return f(pressure, temperature)

    def rho_gas(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.ROGTB.data)

    def rho_oil(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.ROOTB.data)

    def rho_aqu(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.ROWTB.data)

    def drho_oil_dp(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.DROPTB.data)

    def drho_aqu_dp(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.DRWPTB.data)

    def drho_gas_dt(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.DRGTTB.data)

    def drho_oil_dt(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.DROTTB.data)

    def drho_aqu_dt(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.DRWTTB.data)

    def drho_aqu_dt(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.DRWTTB.data)

    def mf_gas_in_gas_and_oil(self, pressure, temperature):
        return self.lookup_olga_table(pressure, temperature, self.RSGTB.data)

    
"RSWTB": {"search": "WATER MASS FRACTION OF GAS", "description": "Water vapour mass fraction in "
"the gas phase"},
"VSGTB": {"search": "GAS VISCOSITY", "description": "Dynamic viscosity for gas"},
"VSOTB": {"search": "LIQ. VISCOSITY", "description": "Dynamic viscosity for oil"},
"VSWTB": {"search": "WAT. VISCOSITY", "description": "Dynamic viscosity for water"},
"CPGTB": {"search": "GAS SPECIFIC HEAT",
"description": "Gas heat capacity at constant pressure"},
"CPOTB": {"search": "LIQ. SPECIFIC HEAT",
"description": "Oil heat capacity at constant pressure"},
"CPWTB": {"search": "WAT. SPECIFIC HEAT",
"description": "Water heat capacity at constant pressure"},
"HGTB": {"search": "GAS ENTHALPY", "description": "Gas enthalpy"},
"HOTB": {"search": "LIQ. ENTHALPY", "description": "Oil enthalpy"},
"HWTB": {"search": "WAT. ENTHALPY", "description": "Water enthalpy"},
"TKGTB": {"search": "GAS THERMAL COND.", "description": "Gas thermal conductivity"},
"TKOTB": {"search": "LIQ. THERMAL COND.", "description": "Oil thermal conductivity"},
"TKWTB": {"search": "WAT. THERMAL COND.", "description": "Water thermal conductivity"},
"SIGOGT": {"search": "SURFACE TENSION GAS/OIL",
"description": "Surface tension between gas and oil"},
"SIGWGT": {"search": "SURFACE TENSION GAS/WATER",
"description": "Surface tension between gas and "
"water"},
"SIGWOT": {"search": "SURFACE TENSION WATER/OIL", "description": "Surface tension between water "
"and oil"},
"SGTB": {"search": "GAS ENTROPY", "description": "Gas specific entropy"},
"SOTB": {"search": "LIQUID ENTROPY", "description": "Oil specific entropy"},
"SWTB": {"search": "WATER ENTROPY", "description": "Water specific entropy"}}
