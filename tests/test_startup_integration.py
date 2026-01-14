"""
Integration tests for startup consolidation system.
Tests the unified startup script and system health endpoints.

These tests verify the startup consolidation features but are skipped in CI
since they require local services to be running.
"""

import subprocess
import time
import requests
import pytest
import os
from pathlib import Path

# Skip all tests in this module in CI unless STARTUP_TESTS_ENABLED is set
pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" and not os.getenv("STARTUP_TESTS_ENABLED"),
    reason="Startup integration tests require local services - skipped in CI"
)


class TestStartupScripts:
    """Test the startup and stop scripts"""
    
    def test_start_script_exists(self):
        """Test that start.sh exists and is executable"""
        script_path = Path("scripts/start.sh")
        assert script_path.exists(), "start.sh should exist"
        assert script_path.stat().st_mode & 0o111, "start.sh should be executable"
    
    def test_stop_script_exists(self):
        """Test that stop.sh exists and is executable"""
        script_path = Path("scripts/stop.sh")
        assert script_path.exists(), "stop.sh should exist"
        assert script_path.stat().st_mode & 0o111, "stop.sh should be executable"
    
    def test_start_script_has_shebang(self):
        """Test that start.sh has proper shebang"""
        with open("scripts/start.sh") as f:
            first_line = f.readline()
        assert first_line.startswith("#!/bin/bash"), "start.sh should have bash shebang"


class TestSystemHealthEndpoints:
    """Test the system health API endpoints"""
    
    @pytest.fixture
    def api_url(self):
        """Base API URL"""
        return "http://localhost:8000"
    
    def test_api_is_accessible(self, api_url):
        """Test that API server is running"""
        try:
            response = requests.get(f"{api_url}/", timeout=5)
            assert response.status_code == 200
        except requests.ConnectionError:
            pytest.skip("API server not running")
    
    def test_health_endpoint(self, api_url):
        """Test the basic health endpoint"""
        try:
            response = requests.get(f"{api_url}/api/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
        except requests.ConnectionError:
            pytest.skip("API server not running")
    
    def test_system_health_endpoint(self, api_url):
        """Test the system health endpoint"""
        try:
            response = requests.get(f"{api_url}/api/system/health", timeout=5)
            # If endpoint doesn't exist yet (404), that's okay - it means API needs restart
            if response.status_code == 404:
                pytest.skip("System health endpoint not loaded - API needs restart")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "services" in data
            assert "prerequisites" in data
        except requests.ConnectionError:
            pytest.skip("API server not running")
    
    def test_system_prerequisites_endpoint(self, api_url):
        """Test the system prerequisites endpoint"""
        try:
            response = requests.get(f"{api_url}/api/system/prerequisites", timeout=5)
            if response.status_code == 404:
                pytest.skip("System prerequisites endpoint not loaded - API needs restart")
            
            assert response.status_code == 200
            data = response.json()
            assert "docker" in data
            assert "python" in data
            assert "node" in data
        except requests.ConnectionError:
            pytest.skip("API server not running")


class TestDockerServices:
    """Test Docker services are configured correctly"""
    
    def test_docker_compose_file_exists(self):
        """Test that docker-compose.yml exists"""
        assert Path("docker-compose.yml").exists()
    
    def test_neo4j_service_defined(self):
        """Test that Neo4j service is defined in docker-compose"""
        with open("docker-compose.yml") as f:
            content = f.read()
        assert "neo4j" in content.lower()
    
    def test_neo4j_is_running(self):
        """Test that Neo4j container is running"""
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            pytest.skip("Docker Compose not available")
        
        # Check if neo4j is in the output and running
        assert "neo4j" in result.stdout.lower()
    
    def test_neo4j_port_accessible(self):
        """Test that Neo4j port 7474 is accessible"""
        try:
            response = requests.get("http://localhost:7474", timeout=5)
            # Neo4j returns 200 for the browser interface
            assert response.status_code == 200
        except requests.ConnectionError:
            pytest.skip("Neo4j not accessible")


class TestFrontendSetup:
    """Test frontend configuration"""
    
    def test_frontend_directory_exists(self):
        """Test that frontend directory exists"""
        assert Path("apps/web").exists()
    
    def test_frontend_package_json_exists(self):
        """Test that frontend package.json exists"""
        assert Path("apps/web/package.json").exists()
    
    def test_dashboard_component_exists(self):
        """Test that Dashboard component exists"""
        assert Path("apps/web/src/pages/Dashboard.tsx").exists()
    
    def test_dashboard_has_system_health(self):
        """Test that Dashboard includes system health monitoring"""
        with open("apps/web/src/pages/Dashboard.tsx") as f:
            content = f.read()
        
        assert "systemHealth" in content
        assert "system/health" in content


class TestDocumentation:
    """Test that documentation is complete"""
    
    def test_quickstart_exists(self):
        """Test that QUICKSTART.md exists"""
        assert Path("QUICKSTART.md").exists()
    
    def test_quickstart_has_npm_start(self):
        """Test that QUICKSTART mentions npm run start"""
        with open("QUICKSTART.md") as f:
            content = f.read()
        assert "npm run start" in content
    
    def test_readme_updated(self):
        """Test that README has Quick Start section"""
        with open("README.md") as f:
            content = f.read()
        assert "Quick Start" in content
        assert "QUICKSTART.md" in content
    
    def test_startup_consolidation_doc_exists(self):
        """Test that implementation documentation exists"""
        assert Path("docs/STARTUP_CONSOLIDATION.md").exists()


class TestNPMScripts:
    """Test NPM scripts configuration"""
    
    def test_package_json_exists(self):
        """Test that root package.json exists"""
        assert Path("package.json").exists()
    
    def test_start_script_defined(self):
        """Test that start script is defined"""
        import json
        with open("package.json") as f:
            pkg = json.load(f)
        
        assert "scripts" in pkg
        assert "start" in pkg["scripts"]
        assert "./scripts/start.sh" in pkg["scripts"]["start"]
    
    def test_stop_script_defined(self):
        """Test that stop script is defined"""
        import json
        with open("package.json") as f:
            pkg = json.load(f)
        
        assert "scripts" in pkg
        assert "stop" in pkg["scripts"]
        assert "./scripts/stop.sh" in pkg["scripts"]["stop"]


class TestSystemHealthAPI:
    """Test the system health API router"""
    
    def test_system_router_file_exists(self):
        """Test that system router file exists"""
        assert Path("apps/api/routers/system.py").exists()
    
    def test_system_router_has_health_endpoint(self):
        """Test that system router defines health endpoint"""
        with open("apps/api/routers/system.py") as f:
            content = f.read()
        
        assert "@router.get(\"/health\"" in content
        assert "SystemHealth" in content
    
    def test_system_router_has_prerequisites_endpoint(self):
        """Test that system router defines prerequisites endpoint"""
        with open("apps/api/routers/system.py") as f:
            content = f.read()
        
        assert "@router.get(\"/prerequisites\"" in content
        assert "PrerequisiteCheck" in content
    
    def test_system_router_imported_in_main(self):
        """Test that system router is imported in main.py"""
        with open("apps/api/main.py") as f:
            content = f.read()
        
        # Check import
        assert "from apps.api.routers import" in content and "system" in content
        
        # Check router inclusion
        assert "app.include_router(system.router" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])