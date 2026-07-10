

## I. Overall Design

```mermaid
flowchart TB
    subgraph Platforms [External Platforms]
        FS[Feishu]
        DT[DingTalk]
        WC[WeCom (In Development)]
        TG[Telegram (In Development)]
        More[More Platforms...]
    end

    subgraph BotModule [bot/ Module]
        WH[Webhook Server]
        Adapters[Platform Adapters]
        Dispatcher[Command Dispatcher]
        Commands[Command Handlers]
    end

    subgraph Core [Existing Core Modules]
        AS[AnalysisService]
        MA[MarketAnalyzer]
        NS[NotificationService]
    end

    FS -->|POST /bot/feishu| WH
    DT -->|POST /bot/dingtalk| WH
    WC -->|POST /bot/wecom| WH
    TG -->|POST /bot/telegram| WH

    WH --> Adapters
    Adapters -->|Unified Message Format| Dispatcher
    Dispatcher --> Commands
    Commands --> AS
    Commands --> MA
    Commands --> NS
```



## II. Directory Structure

Create a `bot/` directory in the project root:

```
bot/
├── __init__.py             # Module entry point, exports main classes
├── models.py               # Unified message/response models
├── dispatcher.py           # Command dispatcher (core)
├── commands/               # Command handlers
│   ├── __init__.py
│   ├── base.py             # Command abstract base class
│   ├── analyze.py          # /analyze stock analysis
│   ├── market.py           # /market market review
│   ├── help.py             # /help help information
│   └── status.py           # /status system status
└── platforms/              # Platform adapters
    ├── __init__.py
    ├── base.py             # Platform abstract base class
    ├── feishu.py           # Feishu Bot
    ├── dingtalk.py         # DingTalk Bot
    ├── dingtalk_stream.py  # DingTalk Bot Stream
    ├── wecom.py            # WeCom Bot (In Development)
    └── telegram.py         # Telegram Bot (In Development)
```

## III. Core Abstract Design

### 3.1 Unified Message Model (`bot/models.py`)

```python
@dataclass
class BotMessage:
    """Unified bot message model"""
    platform: str           # Platform identifier: feishu/dingtalk/wecom/telegram
    user_id: str            # Sender ID
    user_name: str          # Sender name
    chat_id: str            # Chat ID (group or private)
    chat_type: str          # Chat type: group/private
    content: str            # Message text content
    raw_data: Dict          # Raw request data (platform-specific)
    timestamp: datetime     # Message timestamp
    mentioned: bool = False # Whether the bot was @mentioned

@dataclass
class BotResponse:
    """Unified bot response model"""
    text: str               # Reply text
    markdown: bool = False  # Whether it is Markdown
    at_user: bool = True    # Whether to @mention the sender
```

### 3.2 Platform Adapter Base Class (`bot/platforms/base.py`)

```python
class BotPlatform(ABC):
    """Platform adapter abstract base class"""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Platform identifier name"""
        pass
    
    @abstractmethod
    def verify_request(self, headers: Dict, body: bytes) -> bool:
        """Verify request signature (security check)"""
        pass
    
    @abstractmethod
    def parse_message(self, data: Dict) -> Optional[BotMessage]:
        """Parse platform message to unified format"""
        pass
    
    @abstractmethod
    def format_response(self, response: BotResponse) -> Dict:
        """Convert unified response to platform format"""
        pass
```

### 3.3 Command Base Class (`bot/commands/base.py`)

```python
class BotCommand(ABC):
    """Command handler abstract base class"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name (e.g., 'analyze')"""
        pass
    
    @property
    @abstractmethod
    def aliases(self) -> List[str]:
        """Command aliases (e.g., ['a', 'analyze'])"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description"""
        pass
    
    @property
    @abstractmethod
    def usage(self) -> str:
        """Usage instructions"""
        pass
    
    @abstractmethod
    async def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute command"""
        pass
```

### 3.4 Command Dispatcher (`bot/dispatcher.py`)

```python
class CommandDispatcher:
    """Command dispatcher - singleton pattern"""
    
    def __init__(self):
        self._commands: Dict[str, BotCommand] = {}
        self._aliases: Dict[str, str] = {}
    
    def register(self, command: BotCommand) -> None:
        """Register command"""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._aliases[alias] = command.name
    
    def dispatch(self, message: BotMessage) -> BotResponse:
        """Dispatch message to corresponding command"""
        # 1. Parse command and arguments
        # 2. Find command handler
        # 3. Execute and return response
```

## IV. Supported Commands

| Command | Alias | Description | Example |
|------|------|------|------|
| /analyze | /a, analyze | Analyze a specified stock | `/analyze 600519` |
| /market | /m, market | Market review | `/market` |
| /batch | /b, batch | Batch analyze watchlist | `/batch` |
| /help | /h, help | Show help information | `/help` |
| /status | /s, status | System status | `/status` |

## V. `/status` and Model Configuration Diagnostics

### Configurable Levels and Availability Basis

- `/status` LLM availability follows the system's unified runtime priority:
  - `LITELLM_CONFIG` (LiteLLM YAML)
  - `LLM_CHANNELS`
  - Legacy provider keys (`GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY`)
- When the primary model (`LITELLM_MODEL` or `AGENT_LITELLM_MODEL`) has no available source in the currently active layer, it displays "AI Service Not Configured" and retains the user-visible reason line.
- This repository's `requirements.txt` runtime dependency constraint is `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`; within this constraint, this pipeline follows existing compatible behavior.
- This diagnostic rule is consistent with the `GET /api/v1/system/config/setup/status` LLM check: `LITELLM_CONFIG`/`LLM_CHANNELS` have high priority; mode switching does not perform silent migration; switching back to the old mode requires explicit user restoration of historical values or rollback.

### Rollback and Migration Boundaries

- When either `LITELLM_CONFIG` or `LLM_CHANNELS` is active, the underlying legacy configuration is ignored by that layer (will not continue to be used as the current call source).
- Diagnostic enhancement does not perform silent migration: will not actively clear/delete historical values of `GEMINI_*`, `OPENAI_*`, `ANTHROPIC_*`, `LITELLM_*`, only providing availability diagnostics.

### Official Compatibility Sources (For Troubleshooting Reference)

- LiteLLM Official: <https://docs.litellm.ai/>
- LiteLLM OpenAI Compatible: <https://docs.litellm.ai/docs/providers/openai_compatible>
- OpenAI Chat API: <https://platform.openai.com/docs/api-reference/chat>
- DeepSeek API Documentation: <https://api-docs.deepseek.com/>
- Kimi Moonshot Compatibility: <https://platform.moonshot.ai/docs/guide/compatibility>
- Gemini OpenAI Compatibility: <https://ai.google.dev/gemini-api/docs/openai>
- Ollama API Documentation: <https://github.com/ollama/ollama/blob/main/docs/api.md>

## VI. Webhook Routes

Register routes in [api/v1/router.py](../api/v1/router.py):

```python
# Webhook Routes
/bot/feishu      # POST - Feishu event callback
/bot/dingtalk    # POST - DingTalk event callback
/bot/wecom       # POST - WeCom event callback (In Development)
/bot/telegram    # POST - Telegram update callback (In Development)
```

## Configuration

Add bot configuration in [config.py](../config.py):

```python
# === Bot Configuration ===
bot_enabled: bool = False              # Whether to enable the bot
bot_command_prefix: str = "/"          # Command prefix

# Feishu Bot (Event Subscription)
feishu_app_id: str                     # Existing
feishu_app_secret: str                 # Existing
feishu_verification_token: str         # New: Event verification token
feishu_encrypt_key: str                # New: Encryption key

# DingTalk Bot (Application)
dingtalk_app_key: str                  # New
dingtalk_app_secret: str               # New

# WeCom Bot (In Development)
wecom_token: str                       # New: Callback token
wecom_encoding_aes_key: str            # New: EncodingAESKey

# Telegram Bot (In Development)
telegram_bot_token: str                # Existing
telegram_webhook_secret: str           # New: Webhook secret
```

## Extension Notes
### How to Add a New Notification Platform

1. Create a new file in `bot/platforms/`
2. Inherit from the `BotPlatform` base class
3. Implement `verify_request`, `parse_message`, `format_response`
4. Register the Webhook endpoint in the routes

### How to Add a New Command

1. Create a new file in `bot/commands/`
2. Inherit from the `BotCommand` base class
3. Implement the `execute` method
4. Register the command in the dispatcher

## Security Configuration

- Supports command rate limiting (anti-abuse)
- Sensitive operations (e.g., batch analysis) can have permission whitelists configured

Add bot security configuration in [config.py](../config.py):

```python
    bot_rate_limit_requests: int = 10     # Rate limit: max requests within window
    bot_rate_limit_window: int = 60       # Rate limit: window time (seconds)
    bot_admin_users: List[str] = field(default_factory=list)  # Admin user ID list, restricts sensitive operations
```
