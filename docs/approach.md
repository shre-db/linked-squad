# Initially Planned Schema for Multi-Agent Coordination

![Approach](initial_schema.png)

## User Input

A user input could point to:

- **General chat** with the bot
- **Optimization specific** requests

---

## Router Node

A router node acts as a manager interacting with the user and other agents. The node must carefully interpret the user's input and decide one of the following interactions at a time:

1. **General chat**
2. **Delegate task** to Profile Analyzer agent
3. **Delegate task** to Content Rewriter agent
4. **Delegate task** to Job Fit Evaluator agent
5. **Delegate task** to Career Guide agent

### Router Node Behavior

- **General chat**: Router node directly interacts with the user without assistance from other agents
- **Specialized requests**: Router node delegates tasks to respective agents
- **Analysis processing**: Agents perform detailed analysis (with numbers if appropriate) and communicate findings back to the router node
- **Final output**: Router node updates states, post-processes, and presents analysis/reports to the user

---

## Agents

### 1. Profile Analyzer

**Purpose**: Deep analysis of LinkedIn data

**Key Features**:
- Statistics and numerical analysis
- Data visualization capabilities
- Presentation-ready output

**Communication**: 
- Invoked by router node only
- No direct user interaction

### 2. Content Rewriter

**Purpose**: Generate optimized content suggestions based on LinkedIn data

**Key Features**:
- Content optimization recommendations
- Presentation-ready suggestions

**Communication**:
- Invoked by router node only
- No direct user interaction

### 3. Job Fit Evaluator

**Purpose**: Evaluate LinkedIn profile against specific job descriptions

**Key Features**:
- Skills and experience comparison
- Keyword analysis
- Fit score calculation
- Statistical analysis with numbers

**Communication**:
- No direct user interaction
- Presentation-ready output

### 4. Career Guide

**Purpose**: Provide comprehensive career guidance and advice

**Key Features**:
- Career roadmaps
- Tailored strategies
- Resources and recommendations
- Tips & tricks
- Industry insights and "untold truths"
- Enhanced guidance when profile analysis is available

**Communication**:
- Invoked by router node only
- No direct user interaction
- Presentation-ready output

---

## Potential Workflow

The router node checks agent states at every step:

### Step 1: Input Interpretation
- Router node interprets user input

### Step 2: Decision Making
Router decides next action:
- **Direct chat** with user (ask missing information, clarify requirements)
- **Call appropriate agent** best suited for the task
- **Present report** to user

### Step 3: Action Execution
- Setting states
- Responding to user
- Processing agent outputs

---


# Actual Implementation

Using LangGraph to build a sophisticated multi-agent orchestration pattern:

```mermaid
graph TD
    A[User Input] --> B[Router Node]
    
    %% Router's dual functionality
    B --> B1{Router's Instruction<br/>Extraction Unit}
    B1 --> B2[Store Instructions<br/>& Context]
    B1 --> B3{Router's Route Unit}
    
    %% Direct response path
    B3 -->|Direct Response| E[END - Main Chat]
    
    %% Specialized agent paths
    B3 -->|CALL_ANALYZE| C1[Profile Analyzer]
    B3 -->|CALL_REWRITE| C2[Content Rewriter] 
    B3 -->|CALL_JOB_FIT| C3[Job Fit Evaluator]
    B3 -->|CALL_GUIDE| C4[Career Guide]
    
    %% Instructions passed to specialized agents
    B2 -.->|Stored Instructions<br/>& Context| C1
    B2 -.->|Stored Instructions<br/>& Context| C2
    B2 -.->|Stored Instructions<br/>& Context| C3
    B2 -.->|Stored Instructions<br/>& Context| C4
    
    %% Agent processing
    C1 --> D1[Agent Output<br/>+ Set Flags]
    C2 --> D2[Agent Output<br/>+ Set Flags]
    C3 --> D3[Agent Output<br/>+ Set Flags]
    C4 --> D4[Agent Output<br/>+ Set Flags]
    
    %% Post-processing convergence
    D1 --> F[Router's Post<br/>Processing Node]
    D2 --> F
    D3 --> F
    D4 --> F
    
    %% Post-processor also uses stored instructions
    B2 -.->|Stored Instructions<br/>& Context| F
    
    %% Final UI rendering
    F --> G[Main Chat Response]
    D1 -.->|Raw Analysis Report| H[Sidebar: Profile Analysis]
    D2 -.->|Raw Content Suggestions| I[Sidebar: Content Rewrite]
    D3 -.->|Raw Job Fit Report| J[Sidebar: Job Fit Evaluation]
    D4 -.->|Raw Career Guidance| K[Sidebar: Career Guidance]
    
    %% End of turn
    G --> L[End of Turn]
    H -.-> L
    I -.-> L
    J -.-> L
    K -.-> L
    
    %% Styling
    classDef routerNode fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef agentNode fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef postProcess fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef uiNode fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef endNode fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    class B,B1,B2,B3 routerNode
    class C1,C2,C3,C4 agentNode
    class F postProcess
    class G,H,I,J,K uiNode
    class E,L endNode
```

### Implementation Details

#### 1. **Router's Dual Functionality**
- **Instruction Extraction Unit**: Analyzes user input using LLM to extract specific instructions, preferences, and context
- **Route Unit**: Makes intelligent routing decisions based on conversation state and prerequisites

#### 2. **State Management**
- **Conversation History**: Maintains chronological conversation flow
- **Dynamic Instructions**: Stores extracted user preferences for specialized agents
- **Processing Flags**: Coordinates agent output processing (`needs_output_processing`, `pending_agent_output`)
- **Completion Tracking**: Tracks which agents have completed their tasks

#### 3. **Specialized Agent Execution**
- Each agent receives:
  - Primary input data (LinkedIn profile, job description, etc.)
  - **User instructions** from the extraction unit
  - **Conversation context** for continuity
- Agents return **markdown-formatted reports** stored in state
- Agents set processing flags to trigger post-processing

#### 4. **Post-Processing Intelligence**
- Router's post-processing node receives:
  - Raw agent output
  - Stored user instructions
  - Conversation context
- Generates **conversational chat responses** that:
  - Summarize key insights
  - Acknowledge user instructions
  - Guide toward next workflow steps
  - Maintain orchestrator personality

#### 5. **Dual UI Rendering**
- **Main Chat**: Displays post-processor's conversational responses
- **Sidebar**: Shows detailed agent reports in expandable sections
  - Profile Analysis with statistics and metrics
  - Content Rewrite suggestions with multiple options
  - Job Fit Evaluation with scoring and gaps
  - Career Guidance with roadmaps and strategies

#### 6. **Workflow Orchestration**
The system enforces optimal workflow sequencing:
1. **Profile Analysis** (requires LinkedIn URL)
2. **Content Rewriting** (requires completed analysis)
3. **Job Fit Evaluation** (requires analysis + job description)
4. **Career Guidance** (enhanced when other steps completed)

#### 7. **Error Handling & Validation**
- **Prerequisite Validation**: Checks data availability before agent deployment
- **Graceful Degradation**: Each node contains comprehensive error handling
- **State Recovery**: Failed operations clear processing flags appropriately

This implementation enables intelligent conversation flow while maintaining separation between conversational responses and detailed analytical outputs, providing users with both natural interaction and comprehensive insights.


