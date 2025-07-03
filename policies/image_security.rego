# policies/image_security.rego
# Image security and package validation policy

package devcontainer.policies

import future.keywords.if
import future.keywords.in

# Deny dangerous packages in custom images
deny[msg] if {
    input.request.operation == "build_custom_image"
    package := input.request.packages[_]
    package in dangerous_packages
    msg := sprintf("Package '%s' is not allowed in custom images", [package])
}

# Deny privileged operations
deny[msg] if {
    input.request.operation == "create"
    input.request.privileged == true
    input.user.role != "admin"
    msg := "Privileged containers require admin role"
}

# Deny host network mode
deny[msg] if {
    input.request.operation == "create"
    input.request.network_mode == "host"
    msg := "Host network mode is not allowed"
}

# Deny excessive resource requests
deny[msg] if {
    input.request.operation == "create"
    input.request.cpu_limit > max_cpu_for_tier[input.user.tier]
    msg := sprintf("CPU limit %d exceeds maximum %d for tier %s",
                   [input.request.cpu_limit, max_cpu_for_tier[input.user.tier], input.user.tier])
}

deny[msg] if {
    input.request.operation == "create"
    input.request.memory_limit > max_memory_for_tier[input.user.tier]
    msg := sprintf("Memory limit %s exceeds maximum %s for tier %s",
                   [input.request.memory_limit, max_memory_for_tier[input.user.tier], input.user.tier])
}

# Configuration
dangerous_packages := [
    "sudo",
    "docker",
    "docker.io",
    "docker-ce",
    "nmap",
    "wireshark",
    "metasploit",
    "aircrack-ng"
]

max_cpu_for_tier := {
    "free": 2,
    "pro": 4,
    "enterprise": 8
}

max_memory_for_tier := {
    "free": "2g",
    "pro": "8g",
    "enterprise": "32g"
}

# Require image scanning for production
require_image_scan if {
    input.environment == "production"
}

# Validate base images
allowed_base_images := [
    "ubuntu:22.04",
    "ubuntu:24.04",
    "python:3.12",
    "python:3.12-slim",
    "node:20",
    "node:20-slim",
    "golang:1.22",
    "nvidia/cuda:12.2.0-devel-ubuntu22.04"
]

deny[msg] if {
    input.request.operation == "build_custom_image"
    not input.request.base_image in allowed_base_images
    msg := sprintf("Base image '%s' is not in the allowed list", [input.request.base_image])
}
