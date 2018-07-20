
micronix_cmds = {
    'position': 'POS',
    'move_abs': 'MVA',
    'move_rel': 'MVR',
    'acceleration': 'ACC',
    'deceleration': 'DEC',
    'home': 'HOM',
    'zero': 'ZRO',
    'feedback': 'FBK',
    'pid': 'PID',
    'encoder_res': 'ENC',
    'encoder':'EAD',
    'stop': 'STP',
    'emergency_stop':'EST',
    'defaults': 'DEF',
    'save_to_memory':'SAV',
    'velocity': 'VEL',
    'clear_errors': 'CER',
    'resolution': 'REZ',
    'max_acceleration': 'AMX',
    'axis_address': 'ANR',
    'soft_reset': 'RST',
    'deadband': 'DBD',
    'status_byte': 'STA',
    'save_startup_pos':'SVP',
    'sync': 'SYN',
    'neg_lim': 'TLN',
    'pos_lim': 'TLP',
    'encoder_pol': 'EPL',
    'read_errors': 'ERR',
    'version': 'VER',
    'max_velocity': 'VMX',
    'encoder_velocity': 'VRT',
    'enable_limit': 'LCG',
    'motor_pol': 'MPL',
}

oxxius_cmds = {}
import os
import yaml
dirpath = os.path.dirname(os.path.abspath(__file__))
filepath  = os.path.join(dirpath,'oxxius_commands')
with open(filepath, 'r') as f:
    oxxius_cmds = yaml.load(f)

if __name__=='__main__':
    import yaml
    with open('micronix_commands', 'w') as f:
        yaml.dump(micronix_cmds,f,default_flow_style=False)

    #with open('oxxius_commands', 'w') as f:
        #yaml.dump(oxxius_cmds,f,default_flow_style=False)