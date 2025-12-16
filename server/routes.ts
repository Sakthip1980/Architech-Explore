import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { spawn } from "child_process";
import path from "path";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  // Build system from graph
  app.post("/api/simulator/build", async (req, res) => {
    try {
      const graphData = req.body;
      
      const result = await runPythonScript('build_system', graphData);
      res.json(result);
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });
  
  // Run simulation
  app.post("/api/simulator/run", async (req, res) => {
    try {
      const { cycles = 1000, workload = 'memory_intensive' } = req.body;
      
      const result = await runPythonScript('run_simulation', { cycles, workload });
      res.json(result);
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });
  
  // Build and run in one call (avoids process state issues)
  app.post("/api/simulator/build-and-run", async (req, res) => {
    try {
      const { graph, cycles = 1000, workload = 'memory_intensive' } = req.body;
      
      const result = await runPythonScript('build_and_run', { graph, cycles, workload });
      res.json(result);
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });
  
  // Get system status
  app.get("/api/simulator/status", async (req, res) => {
    try {
      const result = await runPythonScript('get_status', {});
      res.json(result);
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });

  // Run workload simulation
  app.post("/api/simulator/workload", async (req, res) => {
    try {
      const { graph, workload } = req.body;
      
      const result = await runPythonScript('run_workload', { graph, workload });
      res.json(result);
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });

  return httpServer;
}

// Helper to run Python scripts
function runPythonScript(command: string, data: any): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonScript = path.join(process.cwd(), 'server', 'simulator_bridge.py');
    const python = spawn('python3', [pythonScript, command, JSON.stringify(data)]);
    
    let stdout = '';
    let stderr = '';
    
    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    python.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `Python process exited with code ${code}`));
      } else {
        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (e) {
          reject(new Error('Failed to parse Python output: ' + stdout));
        }
      }
    });
  });
}
