#!/usr/bin/env python3
"""
Bridge script between Node.js Express and Python simulator
Receives commands via CLI and returns JSON results
"""
import sys
import json
from simulator_api import simulator


def main():
    if len(sys.argv) < 3:
        print(json.dumps({'error': 'Usage: simulator_bridge.py <command> <data>'}))
        sys.exit(1)
    
    command = sys.argv[1]
    data = json.loads(sys.argv[2])
    
    try:
        if command == 'build_system':
            result = simulator.build_system_from_graph(data)
        elif command == 'run_simulation':
            result = simulator.run_simulation(
                cycles=data.get('cycles', 1000),
                workload=data.get('workload', 'memory_intensive')
            )
        elif command == 'get_status':
            result = simulator.get_system_status()
        else:
            result = {'error': f'Unknown command: {command}'}
        
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
