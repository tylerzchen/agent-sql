-- Ticket categories table (reference table)
-- Used for organizing tickets into logical groups (e.g., "Technical Support", "Billing", "Feature Requests")
CREATE TABLE IF NOT EXISTS ticket_categories (
    id BIGSERIAL PRIMARY KEY, -- Unique identifier for category
    organization_id BIGINT NOT NULL REFERENCES organizations(id), -- Links category to specific organization
    name TEXT NOT NULL, -- Category name (e.g., "Technical Support")
    description TEXT, -- Optional description of the category
    parent_id BIGINT REFERENCES ticket_categories(id), -- Self-referencing for hierarchial categories (subcategories)
    is_active BOOLEAN NOT NULL DEFAULT true, -- Whether category is available for new tickets
    created_at TIMESTAMPTZ NOT NULL -- When category was created
);

-- Ticket priorities table (reference table)
-- Defines priority levels for tickets (Low, Normal, High, Critical)
CREATE TABLE IF NOT EXISTS ticket_priorities (
    id SMALLINT PRIMARY KEY, -- Priority ID (1=Low, 2=Normal, 3=High)
    name TEXT NOT NULL UNIQUE, -- Priority name (e.g., "High", "Critical")
    sort_order SMALLINT NOT NULL -- Display order for UI
);

-- Ticket statuses table (reference table)
-- Defines the current state of tickets (New, Open, In Progress, Closed, etc.)
CREATE TABLE IF NOT EXISTS ticket_statuses (
    id SMALLINT PRIMARY KEY, -- Status ID (1=New, 2=Open, 3=In Progress, etc.)
    name TEXT NOT NULL UNIQUE, -- Status name (e.g., "Open", "Closed")
    category TEXT NOT NULL CHECK (category IN ('open', 'pending', 'closed')), -- Status category for filtering
    is_default BOOLEAN NOT NULL DEFAULT false, -- Whether this is the default status for new tickets
    sort_order SMALLINT NOT NULL -- Display order for UI
);

-- Tickets table (main table)
-- Core ticket information and metadata
CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY, -- Unique ticket identifer
    organization_id BIGINT NOT NULL REFERENCES organizations(id), -- Links ticket to specific organization
    user_id BIGINT REFERENCES users(id), -- User who created the ticket (customer)
    agent_id BIGINT REFERENCES agents(id), -- Agent assigned to handle the ticket
    
    -- Ticket identification
    ticket_number TEXT NOT NULL, -- Human-readable ticket number (e.g., "ACME-2024-001")
    subject TEXT NOT NULL, -- Brief description of the issue
    description TEXT, -- Detailed description of the problem
    
    -- Classification (JOIN with reference tables)
    category_id BIGINT REFERENCES ticket_categories(id), -- Links to ticket_categories table
    priority_id SMALLINT NOT NULL REFERENCES ticket_priorities(id), -- Links to ticket_priorities table
    status_id SMALLINT NOT NULL REFERENCES ticket_statuses(id), -- Links to ticket_statuses table
    
    -- Channel tracking
    source_channel TEXT NOT NULL CHECK (source_channel IN ('email', 'web_form', 'phone', 'ai', 'sms', 'api')), -- How ticket was submitted
    
    -- Business logic
    is_case BOOLEAN NOT NULL DEFAULT false, -- Flag for special attention (cases vs regular tickets)
    due_date TIMESTAMPTZ, -- When ticket should be resolved
    first_response_at TIMESTAMPTZ, -- When first response was sent
    resolved_at TIMESTAMPTZ, -- When ticket was marked as resolved
    
    -- Metadata
    custom_fields JSONB DEFAULT '{}', -- Flexible storage for organization-specific fields
    tags TEXT[] DEFAULT '{}', -- Array of tags for categorization and search
    
    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL, -- When ticket was created
    updated_at TIMESTAMPTZ NOT NULL -- When ticket was last modified
);

-- Message types table (reference table)
-- Defines types of messages (note, reply, forward, AI-generated)
CREATE TABLE IF NOT EXISTS message_types (
    id SMALLINT PRIMARY KEY, -- Message type ID (1=note, 2=reply, 3=forward, 4=AI)
    name TEXT NOT NULL UNIQUE -- Message type name (e.g., "reply", "note")
);

-- Messages table
-- All communications related to tickets (emails, notes, replies, etc.)
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY, -- Unique message identifier
    ticket_id BIGINT NOT NULL REFERENCES tickets(id), -- Links message to specific ticket (JOIN key)
    
    -- Author (either agent or user, never both)
    author_agent_id BIGINT REFERENCES agents(id), -- Agent who wrote the message (if agent-authored)
    author_user_id BIGINT REFERENCES users(id), -- User who wrote the message (if user-authored)
    
    -- Message details
    type_id SMALLINT NOT NULL REFERENCES message_types(id), -- Links to message_types table
    subject TEXT, -- Message subject line
    body TEXT NOT NULL, -- Plain text message content
    body_html TEXT, -- Rich text version of message
    
    -- Channel and metadata
    channel TEXT NOT NULL CHECK (channel IN ('email', 'web_form', 'phone', 'ai', 'sms', 'api')), -- How message was sent
    is_public BOOLEAN NOT NULL DEFAULT true, -- False for internal notes, true for customer-visible messages
    
    -- Email-specific fields
    message_id TEXT, -- Email Message-ID header for threading
    in_reply_to TEXT, -- Email In-Reply-To header for threading
    
    -- Audit
    created_at TIMESTAMPTZ NOT NULL, -- When message was created
    updated_at TIMESTAMPTZ NOT NULL -- When message was last modified
);

-- ============================================================================
-- IMPORTANT RELATIONSHIPS FOR SQL QUERIES
-- ============================================================================

-- Primary JOIN relationships:
-- tickets.category_id → ticket_categories.id (for category names)
-- tickets.priority_id → ticket_priorities.id (for priority names)  
-- tickets.status_id → ticket_statuses.id (for status names)
-- messages.ticket_id → tickets.id (for ticket messages)
-- messages.type_id → message_types.id (for message type names)

-- Common JOIN patterns:
-- JOIN tickets t ON m.ticket_id = t.id (get ticket info with messages)
-- JOIN ticket_statuses ts ON t.status_id = ts.id (get status names)
-- JOIN ticket_priorities tp ON t.priority_id = tp.id (get priority names)
-- JOIN ticket_categories tc ON t.category_id = tc.id (get category names)
-- JOIN message_types mt ON m.type_id = mt.id (get message type names)

-- Useful WHERE conditions:
-- ts.category = 'open' (filter by status category)
-- tp.name = 'High' (filter by priority name)
-- tc.name = 'Technical Support' (filter by category name)
-- m.is_public = true (only customer-visible messages)
-- t.is_case = true (only special cases)

-- Common aggregations:
-- COUNT(m.id) as message_count (count messages per ticket)
-- COUNT(t.id) as ticket_count (count tickets by status/priority/category)
-- AVG(EXTRACT(EPOCH FROM (t.resolved_at - t.created_at))/3600) as avg_resolution_hours (average resolution time)