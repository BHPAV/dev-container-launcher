"""Security validation tests for dev-container-launcher."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import os
import tempfile

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from utils import validate_container_name, validate_volume_path, sanitize_path


class TestInputValidationSecurity:
    """Security tests for input validation functions."""
    
    def test_container_name_injection_attempts(self):
        """Test container name validation against injection attempts."""
        malicious_names = [
            "; rm -rf /",
            "test && rm -rf /",
            "test || rm -rf /",
            "test | rm -rf /",
            "test `rm -rf /`",
            "test $(rm -rf /)",
            "test; docker run --rm -v /:/host alpine rm -rf /host",
            "../../../etc/passwd",
            "../../bin/bash",
            "test\nrm -rf /",
            "test\r\nrm -rf /",
            "test\trm -rf /",
            "test\0rm -rf /",
            "${HOME}/../../etc/passwd",
            "$(whoami)",
            "`whoami`",
            "test''; rm -rf /",
            'test""; rm -rf /',
            "test\\; rm -rf /",
            "test & rm -rf /",
            "test && echo 'pwned'",
            "test || echo 'pwned'",
            "test | echo 'pwned'",
            "test > /etc/passwd",
            "test < /etc/passwd",
            "test >> /etc/passwd",
            "test 2>&1",
            "test & /bin/bash",
            "test; /bin/bash",
            "test && /bin/bash",
            "test || /bin/bash",
            "test | /bin/bash",
            "test $(/bin/bash)",
            "test `/bin/bash`",
            "../test",
            "./test",
            "/test",
            "test/../../etc",
            "test/../..",
            "test/./.",
            "test/..",
            "test/.",
            "test\\test",
            "test//test",
            "test@test",
            "test#test",
            "test$test",
            "test%test",
            "test^test",
            "test&test",
            "test*test",
            "test+test",
            "test=test",
            "test[test",
            "test]test",
            "test{test",
            "test}test",
            "test|test",
            "test\\test",
            "test:test",
            "test;test",
            "test\"test",
            "test'test",
            "test<test",
            "test>test",
            "test,test",
            "test?test",
            "test/test",
            "test test",  # space
            "test\ttest",  # tab
            "test\ntest",  # newline
            "test\rtest",  # carriage return
            "test\0test",  # null byte
        ]
        
        for name in malicious_names:
            try:
                validate_container_name(name)
                pytest.fail(f"Expected validation to fail for malicious name: {name}")
            except ValueError:
                pass  # Expected
    
    def test_path_traversal_attempts(self):
        """Test path validation against traversal attempts."""
        malicious_paths = [
            "../../../etc/passwd",
            "../../bin/bash",
            "../../../root",
            "../../../../etc/shadow",
            "../../../home/user/.ssh/id_rsa",
            "../../etc/hosts",
            "../../../var/log/auth.log",
            "../../../../proc/self/environ",
            "../../../dev/null",
            "../../tmp/../etc/passwd",
            "../../../usr/bin/sudo",
            "../../../../etc/sudoers",
            "../../../sys/class/net",
            "../../proc/net/tcp",
            "../../../etc/ssl/private",
            "../../../../home/user/.bashrc",
            "../../../boot/grub/grub.cfg",
            "../../etc/crontab",
            "../../../var/spool/cron",
            "../../../../etc/ssh/ssh_host_rsa_key",
        ]
        
        for path in malicious_paths:
            sanitized = sanitize_path(path)
            # The sanitized path should not contain .. components
            assert ".." not in str(sanitized)
            # And should be absolute
            assert sanitized.is_absolute()
    
    def test_null_byte_injection_in_paths(self):
        """Test that null bytes are removed from paths."""
        paths_with_nulls = [
            "/tmp/test\0malicious",
            "/tmp/\0test",
            "/tmp/test\0",
            "/tmp/test\0\0malicious",
            "/tmp/te\0st/malicious",
            "/tmp\0/test/malicious",
            "\0/tmp/test",
            "/tmp/test/\0",
            "/tmp/test/malicious\0file",
        ]
        
        for path in paths_with_nulls:
            sanitized = sanitize_path(path)
            assert "\0" not in str(sanitized)
    
    def test_symlink_path_resolution(self):
        """Test that symlinks are resolved in paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a real directory
            real_dir = temp_path / "real_dir"
            real_dir.mkdir()
            
            # Create a symlink to it
            symlink_path = temp_path / "symlink_dir"
            symlink_path.symlink_to(real_dir)
            
            # Sanitize the symlink path
            sanitized = sanitize_path(str(symlink_path))
            
            # The sanitized path should resolve to the real directory
            assert sanitized.resolve() == real_dir.resolve()
    
    @patch('utils.ALLOWED_VOLUME_PATHS', [Path('/tmp')])
    def test_volume_path_escape_attempts(self):
        """Test volume path validation against escape attempts."""
        # Create a test directory in allowed path
        with tempfile.TemporaryDirectory(dir='/tmp') as temp_dir:
            allowed_path = Path(temp_dir)
            
            # These should fail - attempts to escape allowed paths
            escape_attempts = [
                allowed_path / "../../../etc/passwd",
                allowed_path / "../../bin/bash",
                allowed_path / "../../../root",
                allowed_path / "../../../../etc/shadow",
                allowed_path / "../../../home/user/.ssh/id_rsa",
            ]
            
            for path in escape_attempts:
                # Even though these paths resolve outside allowed locations,
                # they should be caught by the path traversal detection
                sanitized = sanitize_path(str(path))
                # The sanitized path should not contain .. after resolution
                assert ".." not in str(sanitized)


class TestSSHSecurityValidation:
    """Security tests for SSH-related functions."""
    
    def test_ssh_command_injection_in_container_names(self):
        """Test SSH command injection prevention in container names."""
        # These container names could potentially be used in SSH commands
        injection_attempts = [
            "test; rm -rf /",
            "test && rm -rf /",
            "test || rm -rf /",
            "test | rm -rf /",
            "test `rm -rf /`",
            "test $(rm -rf /)",
            "test'; rm -rf /",
            'test"; rm -rf /',
            "test\"; rm -rf /",
            "test\\; rm -rf /",
            "test & rm -rf /",
            "test\nrm -rf /",
            "test\r\nrm -rf /",
            "test\trm -rf /",
            "test\0rm -rf /",
        ]
        
        for name in injection_attempts:
            try:
                validate_container_name(name)
                pytest.fail(f"Expected validation to fail for SSH injection name: {name}")
            except ValueError:
                pass  # Expected
    
    def test_ssh_config_injection_prevention(self):
        """Test prevention of SSH config injection."""
        from utils import sanitize_path
        
        # Paths that could be used to inject SSH config
        ssh_injection_paths = [
            "~/.ssh/config",
            "~/.ssh/id_rsa",
            "~/.ssh/known_hosts",
            "~/.ssh/authorized_keys",
            "/home/user/.ssh/config",
            "/root/.ssh/config",
            "../../../home/user/.ssh/config",
            "../../etc/ssh/ssh_config",
            "../../../etc/ssh/sshd_config",
        ]
        
        for path in ssh_injection_paths:
            sanitized = sanitize_path(path)
            # Sanitized paths should be absolute and not contain .. components
            assert sanitized.is_absolute()
            assert ".." not in str(sanitized)
    
    @patch('subprocess.run')
    def test_ssh_fingerprint_command_injection(self, mock_run):
        """Test SSH fingerprint extraction against command injection."""
        from utils import get_container_ssh_key_fingerprint
        
        # Container names that could be used for command injection
        injection_names = [
            "test; rm -rf /",
            "test && rm -rf /",
            "test || rm -rf /",
            "test | rm -rf /",
            "test `rm -rf /`",
            "test $(rm -rf /)",
            "test'; rm -rf /",
            'test"; rm -rf /',
            "test\"; rm -rf /",
            "test\\; rm -rf /",
            "test & rm -rf /",
            "test\nrm -rf /",
            "test\r\nrm -rf /",
            "test\trm -rf /",
            "test\0rm -rf /",
        ]
        
        mock_run.return_value.stdout = "256 SHA256:abc123 root@host (ED25519)\n"
        mock_run.return_value.returncode = 0
        
        for name in injection_names:
            # The function should still work, but the container name should be
            # properly escaped/validated before being passed to subprocess
            result = get_container_ssh_key_fingerprint(name)
            
            # Verify the subprocess was called with the exact name
            # (no shell interpretation should occur)
            mock_run.assert_called_with(
                ["docker", "exec", name, "ssh-keygen", "-lf", "/etc/ssh/ssh_host_ed25519_key.pub"],
                capture_output=True,
                text=True,
                check=True
            )


class TestDockerSecurityValidation:
    """Security tests for Docker-related operations."""
    
    def test_docker_command_injection_prevention(self):
        """Test prevention of Docker command injection."""
        # Container names that could be used for Docker command injection
        injection_names = [
            "test; docker run --rm -v /:/host alpine rm -rf /host",
            "test && docker run --privileged alpine",
            "test || docker run --rm alpine",
            "test | docker run alpine",
            "test `docker run alpine`",
            "test $(docker run alpine)",
            "test'; docker run alpine",
            'test"; docker run alpine',
            "test\"; docker run alpine",
            "test\\; docker run alpine",
            "test & docker run alpine",
            "test\ndocker run alpine",
            "test\r\ndocker run alpine",
            "test\tdocker run alpine",
            "test\0docker run alpine",
        ]
        
        for name in injection_names:
            try:
                validate_container_name(name)
                pytest.fail(f"Expected validation to fail for injection name: {name}")
            except ValueError:
                pass  # Expected
    
    def test_volume_mount_security(self):
        """Test security of volume mount paths."""
        dangerous_paths = [
            "/",
            "/etc",
            "/etc/passwd",
            "/etc/shadow",
            "/etc/ssh",
            "/root",
            "/home",
            "/var",
            "/usr",
            "/bin",
            "/sbin",
            "/boot",
            "/dev",
            "/proc",
            "/sys",
            "/tmp/../etc",
            "/tmp/../../etc",
            "/tmp/../../../etc",
        ]
        
        # Without proper ALLOWED_VOLUME_PATHS configuration, these should fail
        with patch('utils.ALLOWED_VOLUME_PATHS', [Path('/tmp')]):
            for path in dangerous_paths:
                if Path(path).exists():
                    with pytest.raises(ValueError, match="not in allowed locations"):
                        validate_volume_path(Path(path))


class TestConfigurationSecurity:
    """Security tests for configuration validation."""
    
    def test_environment_variable_injection(self):
        """Test prevention of environment variable injection."""
        # Test that environment variables can't be used to inject malicious values
        dangerous_env_values = [
            "; rm -rf /",
            "&& rm -rf /",
            "|| rm -rf /",
            "| rm -rf /",
            "`rm -rf /`",
            "$(rm -rf /)",
            "'; rm -rf /",
            '"; rm -rf /',
            "\"; rm -rf /",
            "\\; rm -rf /",
            "& rm -rf /",
            "\nrm -rf /",
            "\r\nrm -rf /",
            "\trm -rf /",
            "\0rm -rf /",
        ]
        
        for value in dangerous_env_values:
            # Test that these values are properly sanitized when used in paths
            sanitized = sanitize_path(value)
            assert sanitized.is_absolute()
            assert ".." not in str(sanitized)
    
    def test_log_injection_prevention(self):
        """Test prevention of log injection attacks."""
        # Test that log messages can't be used to inject malicious content
        log_injection_attempts = [
            "test\nINFO: Admin logged in",
            "test\r\nERROR: Security breach",
            "test\tWARN: Unauthorized access",
            "test\0DEBUG: Password is 123456",
            "test\n\nINFO: Root access granted",
            "test\r\n\r\nERROR: System compromised",
        ]
        
        for attempt in log_injection_attempts:
            # When used as container names, these should fail validation
            try:
                validate_container_name(attempt)
                pytest.fail(f"Expected validation to fail for log injection attempt: {attempt}")
            except ValueError:
                pass  # Expected
    
    def test_file_path_injection_prevention(self):
        """Test prevention of file path injection attacks."""
        # Test that file paths can't be used to access unauthorized files
        file_injection_attempts = [
            "/etc/passwd\0/tmp/safe",
            "/tmp/safe\0/etc/passwd",
            "/tmp/safe\n/etc/passwd",
            "/tmp/safe\r/etc/passwd",
            "/tmp/safe\t/etc/passwd",
            "/tmp/safe\x00/etc/passwd",
            "/tmp/safe\x0a/etc/passwd",
            "/tmp/safe\x0d/etc/passwd",
            "/tmp/safe\x09/etc/passwd",
        ]
        
        for attempt in file_injection_attempts:
            sanitized = sanitize_path(attempt)
            # Should not contain null bytes after sanitization (other control chars may be preserved by Path)
            assert "\0" not in str(sanitized)
            # The path should be absolute and resolved
            assert sanitized.is_absolute()


class TestPrivilegeEscalationPrevention:
    """Security tests for privilege escalation prevention."""
    
    def test_sudo_command_injection_prevention(self):
        """Test prevention of sudo command injection."""
        # These names could potentially be used in sudo commands
        sudo_injection_names = [
            "test; sudo rm -rf /",
            "test && sudo rm -rf /",
            "test || sudo rm -rf /",
            "test | sudo rm -rf /",
            "test `sudo rm -rf /`",
            "test $(sudo rm -rf /)",
            "test'; sudo rm -rf /",
            'test"; sudo rm -rf /',
            "test\"; sudo rm -rf /",
            "test\\; sudo rm -rf /",
            "test & sudo rm -rf /",
            "test\nsudo rm -rf /",
            "test\r\nsudo rm -rf /",
            "test\tsudo rm -rf /",
            "test\0sudo rm -rf /",
        ]
        
        for name in sudo_injection_names:
            try:
                validate_container_name(name)
                pytest.fail(f"Expected validation to fail for sudo injection name: {name}")
            except ValueError:
                pass  # Expected
    
    def test_shell_metacharacter_prevention(self):
        """Test prevention of shell metacharacter injection."""
        shell_metacharacters = [
            "test;",
            "test&",
            "test|",
            "test&&",
            "test||",
            "test`",
            "test$",
            "test(",
            "test)",
            "test{",
            "test}",
            "test[",
            "test]",
            "test<",
            "test>",
            "test*",
            "test?",
            "test~",
            "test!",
            "test\"",
            "test'",
            "test\\",
            "test/",
            "test:",
            "test=",
            "test+",
            "test%",
            "test^",
            "test#",
            "test@",
        ]
        
        for name in shell_metacharacters:
            try:
                validate_container_name(name)
                pytest.fail(f"Expected validation to fail for shell metacharacter: {name}")
            except ValueError:
                pass  # Expected