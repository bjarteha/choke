from ParseOlgaPvt import OlgaPvt

path = "C:\\Data\\WorkArea\\Choke Sizing Tool Upgrade 2020 - Choke models\\Choke code\\OLGA_PVT_TAB\\OLGA PVT files examples\\"
file = "E1_Tuned.tab"

pvt_file = path + file

pvt = OlgaPvt(pvt_file)
pvt.read_pvt()

