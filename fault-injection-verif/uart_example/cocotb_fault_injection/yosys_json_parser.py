import json
from collections import defaultdict


def parse_ff_info(json_file):
    with open(json_file, 'r') as f:
        yosys_design = json.load(f)

    ff_info = defaultdict(list)

    for module_name, module in yosys_design.get("modules", {}).items():
        for cell_name, cell in module.get("cells", {}).items():
            cell_type = cell.get("type", "")
            if cell_type not in ["$dff", "$dffsr", "$adff"]:
                continue

            ctrl = []
            q_sig = cell["connections"].get("Q", [])
            if not q_sig or len(q_sig) != 1:
                continue

            q_raw = q_sig[0]
            q_name = str(q_raw).lstrip("\\") if isinstance(q_raw, str) else f"sig_{q_raw}"

            ff = {"q": q_name, "ctrl": []}

            if cell_type == "$dffsr":
                if "SET" in cell["connections"]:
                    s_raw = cell["connections"]["SET"][0]
                    s_name = str(s_raw).lstrip("\\") if isinstance(s_raw, str) else f"set_{s_raw}"
                    s_pol = cell.get("parameters", {}).get("SET_POLARITY", 1)
                    ff["ctrl"].append((s_name, s_pol))

                if "CLR" in cell["connections"]:
                    r_raw = cell["connections"]["CLR"][0]
                    r_name = str(r_raw).lstrip("\\") if isinstance(r_raw, str) else f"clr_{r_raw}"
                    r_pol = cell.get("parameters", {}).get("CLR_POLARITY", 1)
                    ff["ctrl"].append((r_name, r_pol))

            elif cell_type == "$adff":
                if "ARST" in cell["connections"]:
                    r_raw = cell["connections"]["ARST"][0]
                    r_name = str(r_raw).lstrip("\\") if isinstance(r_raw, str) else f"arst_{r_raw}"
                    r_pol = cell.get("parameters", {}).get("ARST_POLARITY", 1)
                    ff["ctrl"].append((r_name, r_pol))

            ff_info[module_name].append(ff)

    return ff_info
