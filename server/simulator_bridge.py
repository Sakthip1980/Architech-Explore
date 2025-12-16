#!/usr/bin/env python3
"""
Bridge script between Node.js Express and Python simulator
Receives commands via CLI and returns JSON results
"""
import sys
import os
import json

# Add project root to path (this script runs from server/ directory)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
        elif command == 'build_and_run':
            result = simulator.build_and_run(
                graph_data=data.get('graph', {}),
                cycles=data.get('cycles', 1000),
                workload=data.get('workload', 'memory_intensive')
            )
        elif command == 'get_status':
            result = simulator.get_system_status()
        else:
            result = {'error': f'Unknown command: {command}'}
        
        print(json.dumps(result))
    except Exception as e:
        import traceback
        error_info = {'error': str(e), 'traceback': traceback.format_exc()}
        print(json.dumps(error_info))
        sys.exit(1)


if __name__ == '__main__':
    main()
