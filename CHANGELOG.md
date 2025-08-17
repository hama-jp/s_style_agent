# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-01-17

### Added
- **MCP Trace Display**: Detailed MCP call status visualization in execution traces
  - Real-time tracking of MCP tool calls with success/failure status
  - Execution duration and parameter logging for MCP operations
  - Integrated trace viewer showing MCP metadata

- **Auto Error Recovery**: Intelligent S-expression syntax error recovery
  - Automatic detection of syntax errors (e.g., missing brackets)
  - LLM-based regeneration with full error context
  - Multi-attempt recovery with detailed logging
  - Seamless integration with both CLI and TUI modes

- **TUI Integration**: Rich text user interface with enhanced user experience
  - 4-tab layout: Dashboard, Workspace, History, Settings
  - Real-time execution tracing with visual feedback
  - Complete S-expression display (no truncation)
  - Keyboard shortcuts for efficient navigation

- **Unified Architecture**: Shared processing foundation
  - Common AgentService for CLI and TUI consistency
  - Unified ToolExecutor for consistent tool execution
  - Shared trace logging across all interfaces
  - CLI as testing interface for TUI functionality

### Enhanced
- **Execution Tracing**: 
  - Complete S-expression display in trace viewer
  - Detailed metadata collection for all operations
  - Provenance tracking (LLM/MCP/Built-in)
  - JSON-L format trace export

- **Error Handling**:
  - Comprehensive error context preservation
  - Retry mechanisms with exponential backoff
  - User-friendly error messages
  - Graceful degradation on failures

### Technical Improvements
- Extended TraceLogger with MCP-specific metadata fields
- Implemented robust S-expression validation
- Added AsyncContextualEvaluator trace integration
- Enhanced tool execution with detailed logging
- Improved error propagation and handling

### Bug Fixes
- Fixed S-expression truncation in TUI displays
- Resolved trace entry type mismatches
- Corrected MCP metadata update timing
- Fixed regex matching issues in code replacement

## [1.0.0] - 2025-01-15

### Added
- Initial S-expression agent system implementation
- Basic S-expression parser and evaluator
- CLI interface with interactive commands
- Built-in tools (calc, notify, search, math)
- MCP (Model Context Protocol) integration
- LangChain/LangGraph tracing support
- Multi-LLM provider support (OpenAI, Anthropic, Local)
- Configuration management via environment variables
- Comprehensive test suite
- GitHub Actions CI/CD pipeline
- Multi-language documentation (English/Japanese)

### Features
- Synchronous and asynchronous S-expression evaluation
- Parallel execution with `(par ...)` construct
- Context-aware evaluation with variable binding
- User interaction tools (`ask_user`, `collect_info`)
- Mathematical processing with SymPy integration
- External API integration via MCP
- Session history and state management
- Robust error handling and validation

---

**Legend:**
- 🎯 **Added**: New features and capabilities
- 🔧 **Enhanced**: Improvements to existing features  
- 🐛 **Fixed**: Bug fixes and corrections
- 💥 **Breaking**: Breaking changes requiring migration

For more details on each release, see the [GitHub Releases](https://github.com/hama-jp/s_style_agent/releases) page.