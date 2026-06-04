from define_class import *

def read_2e_ctp_instance(file_path):
    header = {}
    demands = {}
    covers = {}
    hubs = {}

    section_list = [
        'NODE_COORD_SECTION',
        'DEMAND_SECTION',
        'DEMAND_SERVICE_SECTION',
        'COVERING_COORD_SECTION',
        'COVERING_SERVICE_SECTION',
        'HUB_COORD_SECTION',
        'HUB_SERVICE_SECTION',
    ]
    current_section = None

    with open(file_path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line == 'EOF':
                continue

            # Header lines (assume KEY : VALUE)
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip().upper()
                val = val.strip()
                
                if key == 'DEPOT':
                    parts = val.split()
                    DEPOT = (float(parts[-2]), float(parts[-1]))
                    header[key] = val
                    continue
                
                # try numeric conversion
                if '.' in val:
                    header[key] = float(val)
                else:
                    try:
                        header[key] = int(val)
                    except ValueError:
                        header[key] = val

                continue

            # Section markers
            matched = False
            for section in section_list:
                if section in line:
                    current_section = section
                    matched = True
                    break
            if matched:
                continue
            if current_section is None:
                continue

            parts = line.split()
            cover_offset = 1000  # to avoid ID clashes with demands
            hub_offset = 2000  # to avoid ID clashes with demands and covers
            
            if current_section == 'NODE_COORD_SECTION':
                demands[int(parts[0])] = Demand(id=int(parts[0]), x=float(parts[1]), y=float(parts[2]))

            elif current_section == 'DEMAND_SECTION':
                demands[int(parts[0])].demand = float(parts[1])
                
            elif current_section == 'DEMAND_SERVICE_SECTION':
                demands[int(parts[0])].service_time = float(parts[1])

            elif current_section == 'COVERING_COORD_SECTION':
                covers[int(parts[0]) + cover_offset] = Cover(id=int(parts[0]) + cover_offset, x=float(parts[1]), y=float(parts[2]))
            
            elif current_section == 'COVERING_SERVICE_SECTION':
                covers[int(parts[0]) + cover_offset].service_time = float(parts[1])
                
            elif current_section == 'HUB_COORD_SECTION':
                hubs[int(parts[0]) + hub_offset] = Hub(id=int(parts[0]) + hub_offset, x=float(parts[1]), y=float(parts[2]))
            
            elif current_section == 'HUB_SERVICE_SECTION':
                hubs[int(parts[0]) + hub_offset].service_time = float(parts[1])

    return Instance(
        NAME=header['NAME'],
        CAPACITY1=header['CAPACITY1'],
        CAPACITY2=header['CAPACITY2'],
        COST1=header['COST1'],
        COST2=header['COST2'],
        TIME1=header['TIME1'],
        TIME2=header['TIME2'],
        TIME3=header['TIME3'],
        DEPOT=DEPOT, 
        demands=demands, 
        covers=covers, 
        hubs=hubs,
        )