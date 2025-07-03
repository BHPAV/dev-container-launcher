# Dev-Container Launcher Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Interfaces                           │
├─────────────────────┬───────────────────┬─────────────────────────┤
│   Textual TUI      │     Web UI        │      CLI (devctl)       │
│    (app.py)        │  (React + API)    │   (Click commands)      │
└─────────────────────┴───────────────────┴─────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Core Service Layer                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐              │
│  │   devctl    │  │   FastAPI    │  │    Auth     │              │
│  │    Core     │  │   Service    │  │   Module    │              │
│  └─────────────┘  └──────────────┘  └─────────────┘              │
│         │                 │                  │                      │
│         └─────────────────┴──────────────────┘                     │
│                           │                                         │
│                    ┌──────▼──────┐                                 │
│                    │   Models    │                                 │
│                    │ (Pydantic)  │                                 │
│                    └─────────────┘                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Data & Storage Layer                         │
├─────────────────────┬──────────────────┬──────────────────────────┤
│    Docker Engine    │     Neo4j        │    File System           │
│   (Containers)      │  (Graph DB)      │  (SSH Config)            │
└─────────────────────┴──────────────────┴──────────────────────────┘
```

## Component Details

### 1. User Interfaces

#### Textual TUI (`app.py`)
- Terminal-based interface using Textual framework
- Real-time container status updates
- Keyboard shortcuts for quick actions
- Cross-platform compatibility

#### Web UI (React + FastAPI)
- Modern React frontend with TypeScript
- Real-time updates via WebSocket
- Responsive design for desktop and mobile
- Advanced container management features

#### CLI (`devctl`)
- Command-line interface using Click
- Scriptable for automation
- Direct access to all core functionality

### 2. Core Service Layer

#### devctl Core
- Container lifecycle management
- Docker API abstraction
- SSH configuration management
- Volume and port management

#### FastAPI Service
- RESTful API endpoints
- WebSocket support for real-time updates
- OpenAPI documentation
- JWT authentication

#### Auth Module
- SSH key management
- Certificate Authority (CA) support
- User authentication and authorization
- Token management

### 3. Data & Storage Layer

#### Docker Engine
- Container runtime
- Image management
- Network and volume handling
- Resource isolation

#### Neo4j Graph Database
- Container metadata storage
- User activity tracking
- Relationship mapping
- Analytics and reporting

#### File System
- SSH configuration (~/.ssh/config)
- Persistent volume data
- Container templates
- Configuration files

## Data Flow

### Container Creation Flow
```
User Request → UI → API → Core → Docker Engine
                            ↓
                         Neo4j ← Record metadata
                            ↓
                      SSH Config ← Update
                            ↓
                     Response → UI → User
```

### Authentication Flow
```
User Login → Web UI → API → Auth Module
                              ↓
                         Validate → JWT
                              ↓
                    Authorized Request → Service
```

## Security Architecture

### Network Security
```
┌─────────────────────────────────────────┐
│          External Network               │
│                                         │
│  Users ─── HTTPS ──→ Web UI/API        │
│                                         │
└─────────────────────────────────────────┘
                    │
              Firewall/Proxy
                    │
┌─────────────────────────────────────────┐
│          Internal Network               │
│                                         │
│  API ←─→ Docker ←─→ Containers         │
│   ↓                                     │
│  Neo4j                                  │
│                                         │
└─────────────────────────────────────────┘
```

### Container Isolation
- Each container runs with limited privileges
- Network isolation between containers
- Resource limits enforced
- Secure SSH access only

## Scalability Considerations

### Phase 1: Single Host
- All components on one machine
- Suitable for individual developers
- Up to 50 concurrent containers

### Phase 2: Multi-Host (Planned)
```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Host 1  │     │  Host 2  │     │  Host 3  │
│ Primary  │     │Secondary │     │Secondary │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     └────────────────┴────────────────┘
              Message Bus (Redis/RabbitMQ)
```

### Phase 3: Cloud Native (Future)
- Kubernetes orchestration
- Cloud provider integration
- Auto-scaling capabilities
- Global distribution

## Technology Stack

### Backend
- **Python 3.10+**: Core language
- **FastAPI**: API framework
- **Docker SDK**: Container management
- **Neo4j**: Graph database
- **Click**: CLI framework
- **Textual**: TUI framework

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **Vite**: Build tool
- **React Query**: Data fetching
- **Socket.io**: Real-time updates

### Infrastructure
- **Docker Engine**: Container runtime
- **OpenSSH**: Secure access
- **Nginx**: Reverse proxy (optional)
- **Prometheus**: Metrics (optional)
- **Grafana**: Monitoring (optional)

## Performance Targets

- Container creation: < 5 seconds
- API response time: < 200ms (p95)
- UI update latency: < 100ms
- Concurrent containers: 100+
- System uptime: 99.9%

## Monitoring Points

1. **System Metrics**
   - Container count
   - CPU/Memory usage
   - Disk I/O
   - Network traffic

2. **Application Metrics**
   - API request rate
   - Error rate
   - Response times
   - Active sessions

3. **Business Metrics**
   - Container creation rate
   - User activity
   - Image usage statistics
   - Session duration

## Disaster Recovery

1. **Backup Strategy**
   - Container configurations
   - User workspace volumes
   - Neo4j database
   - SSH keys and certificates

2. **Recovery Procedures**
   - Container recreation from metadata
   - Volume restoration
   - Configuration rebuild
   - Certificate regeneration

## Future Enhancements

1. **AI/ML Integration**
   - Intelligent resource allocation
   - Usage pattern analysis
   - Predictive scaling

2. **Advanced Features**
   - Live container migration
   - Collaborative development
   - IDE plugins
   - Mobile app

3. **Enterprise Features**
   - LDAP/AD integration
   - Audit logging
   - Compliance reporting
   - SLA management
