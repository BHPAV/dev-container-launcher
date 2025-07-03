# policies/container_quota.rego
# Container quota enforcement policy

package devcontainer.policies

import future.keywords.if
import future.keywords.in

# Default deny
default allow = false

# Allow if user is admin
allow if {
    input.user.role == "admin"
}

# Allow if user has not exceeded quota
allow if {
    input.request.operation == "create"
    count(user_containers[input.user.id]) < max_containers_per_user
}

# Allow read operations
allow if {
    input.request.operation in ["list", "get", "logs"]
}

# Deny with specific message if quota exceeded
deny[msg] if {
    input.request.operation == "create"
    count(user_containers[input.user.id]) >= max_containers_per_user
    msg := sprintf("User %s has reached the maximum of %d containers", 
                   [input.user.username, max_containers_per_user])
}

# Configuration
max_containers_per_user := 2 if {
    input.user.tier == "free"
} else := 5 if {
    input.user.tier == "pro"
} else := 10

# Helper: Get user's containers from graph data
user_containers[user_id] := containers if {
    containers := [c | 
        c := data.containers[_]
        c.owner_id == user_id
        c.status in ["running", "stopped"]
    ]
}
