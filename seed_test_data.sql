-- Seed test data for verification tests

-- Create test policy
INSERT INTO scan_policies (
    id, name, description, allowed_cidrs, blocked_cidrs, 
    max_targets, max_scan_rate, provider_restrictions, is_enabled,
    created_at, updated_at
) VALUES (
    'c001e000-0000-0000-0000-000000000001'::uuid,
    'test-policy',
    'Test policy for verification',
    '["127.0.0.0/8", "10.0.0.0/8", "192.168.0.0/16"]'::jsonb,
    '[]'::jsonb,
    100,
    1000,
    '{}'::jsonb,
    true,
    NOW(),
    NOW()
);

-- Create test scanner profile
INSERT INTO scanner_profiles (
    id, name, provider, description, configuration, is_enabled,
    created_at, updated_at
) VALUES (
    'c002e000-0000-0000-0000-000000000001'::uuid,
    'test-nmap',
    'nmap',
    'Test nmap profile',
    '{"timing": "T3"}'::jsonb,
    true,
    NOW(),
    NOW()
);

