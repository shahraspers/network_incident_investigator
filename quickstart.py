#!/usr/bin/env python
"""
Quick start script for Network Incident Investigator
Helps set up and run the system.
"""
import os
import sys
import subprocess
from pathlib import Path
import argparse


def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_success(text):
    """Print success message"""
    print(f"✅ {text}")


def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")


def print_warning(text):
    """Print warning message"""
    print(f"⚠️  {text}")


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_warning(f"Python 3.8+ required. You have {version.major}.{version.minor}")
        return False
    
    print_success(f"Python {version.major}.{version.minor} detected")
    return True


def check_dependencies():
    """Check if key dependencies are installed"""
    print_header("Checking Dependencies")
    
    required = ['pandas', 'numpy', 'sklearn', 'fastapi', 'streamlit']
    missing = []
    
    for package in required:
        try:
            __import__(package if package != 'sklearn' else 'sklearn')
            print_success(f"{package} installed")
        except ImportError:
            print_warning(f"{package} not found")
            missing.append(package)
    
    return len(missing) == 0


def install_dependencies():
    """Install dependencies from requirements.txt"""
    print_header("Installing Dependencies")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print_warning(f"requirements.txt not found at {requirements_file}")
        return False
    
    try:
        print_info(f"Installing from {requirements_file}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
        print_success("Dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print_warning("Failed to install dependencies")
        return False


def generate_sample_data():
    """Generate sample data"""
    print_header("Generating Sample Data")
    
    try:
        from data.cell_site_kpi_generator import generate_synthetic_kpi_data
        
        print_info("Generating 3 sites × 24 hours...")
        df = generate_synthetic_kpi_data(
            num_sites=3,
            num_hours=24,
            interval_minutes=5,
            output_dir="./data",
            save_files=True
        )
        
        print_success(f"Generated {len(df)} rows of data")
        return True
    except Exception as e:
        print_warning(f"Error generating sample data: {e}")
        return False


def run_frontend():
    """Run Streamlit frontend"""
    print_header("Starting Streamlit Frontend")
    
    app_path = Path(__file__).parent / "frontend" / "app.py"
    
    if not app_path.exists():
        print_warning(f"app.py not found at {app_path}")
        return False
    
    try:
        print_info("Starting Streamlit server...")
        print_info("Open browser to: http://localhost:8501")
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])
        return True
    except Exception as e:
        print_warning(f"Error running frontend: {e}")
        return False


def run_backend():
    """Run FastAPI backend"""
    print_header("Starting FastAPI Backend")
    
    try:
        print_info("Starting API server...")
        print_info("API docs available at: http://localhost:8000/docs")
        subprocess.run([sys.executable, "-m", "backend.api"])
        return True
    except Exception as e:
        print_warning(f"Error running backend: {e}")
        return False


def run_tests():
    """Run unit tests"""
    print_header("Running Tests")
    
    try:
        import pytest
        print_info("Running pytest...")
        pytest.main(["tests/", "-v"])
        return True
    except ImportError:
        print_warning("pytest not installed. Install with: pip install pytest")
        return False
    except Exception as e:
        print_warning(f"Error running tests: {e}")
        return False


def run_demo():
    """Run a quick demo"""
    print_header("Running Quick Demo")
    
    try:
        from data.cell_site_kpi_generator import generate_synthetic_kpi_data
        from services.anomaly_detection.kpi_detector import detect_anomalies
        from services.genai_reasoning.context_builder import build_anomaly_context
        
        print_info("Step 1: Generating synthetic data...")
        df = generate_synthetic_kpi_data(num_sites=2, num_hours=6, save_files=False)
        print_success(f"Generated {len(df)} rows")
        
        print_info("Step 2: Detecting anomalies...")
        result_df = detect_anomalies(
            df=df,
            metrics=["rsrp", "throughput_mbps", "latency_ms"],
            method="zscore"
        )
        
        anomaly_count = result_df["is_anomaly"].sum()
        print_success(f"Detected {anomaly_count} anomalies")
        
        print_info("Step 3: Building anomaly context...")
        if anomaly_count > 0:
            anomalies = result_df[result_df["is_anomaly"]]
            anomaly_row = anomalies.iloc[0]
            
            context = build_anomaly_context(
                df=result_df,
                anomaly_row=anomaly_row,
                metric_columns=["rsrp", "throughput_mbps", "latency_ms"]
            )
            
            print_success(f"Context built for {context['site_id']}")
            print(f"\nContext summary:")
            print(f"  Site: {context['site_id']}")
            print(f"  Anomalies: {len(context['anomalies'])}")
            print(f"  Indicators: {context['incident_indicators']}")
        
        print_success("Demo completed!")
        return True
        
    except Exception as e:
        print_warning(f"Error running demo: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Network Incident Investigator - Quick Start"
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        choices=["setup", "frontend", "backend", "both", "test", "demo", "data"],
        default="setup",
        help="Command to run"
    )
    
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency check"
    )
    
    args = parser.parse_args()
    
    print_header("Network Incident Investigator")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Handle commands
    if args.command == "setup":
        print_header("Setup & Configuration")
        
        # Check dependencies
        if not args.skip_deps and not check_dependencies():
            print_info("Installing missing dependencies...")
            if not install_dependencies():
                sys.exit(1)
        
        # Generate sample data
        if generate_sample_data():
            print_success("Setup complete!")
            print("\nNext steps:")
            print("  1. Run frontend:  python quickstart.py frontend")
            print("  2. Run backend:   python quickstart.py backend")
            print("  3. Run both:      python quickstart.py both")
            print("  4. Try demo:      python quickstart.py demo")
    
    elif args.command == "frontend":
        run_frontend()
    
    elif args.command == "backend":
        run_backend()
    
    elif args.command == "both":
        print_warning("Running both - use separate terminals!")
        print_info("Terminal 1: python quickstart.py backend")
        print_info("Terminal 2: python quickstart.py frontend")
        
        try:
            run_backend()
        except KeyboardInterrupt:
            print("\nShutdown...")
    
    elif args.command == "test":
        run_tests()
    
    elif args.command == "demo":
        run_demo()
    
    elif args.command == "data":
        generate_sample_data()


if __name__ == "__main__":
    main()
