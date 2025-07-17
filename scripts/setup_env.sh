#!/bin/bash
# Setup environment files for deployment

echo "Setting up environment configuration..."

# Function to prompt for API keys
prompt_for_keys() {
    echo ""
    echo "API Key Configuration"
    echo "===================="
    echo "At least one API key is required for AI comparisons."
    echo ""
    
    # Check if .env.keys already exists
    if [ -f ".env.keys" ]; then
        echo "Found existing .env.keys file."
        read -p "Do you want to update it? (y/N): " update_keys
        if [[ ! "$update_keys" =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    # Create .env.keys
    echo "# API Keys - DO NOT COMMIT THIS FILE!" > .env.keys
    echo "# Generated on $(date)" >> .env.keys
    echo "" >> .env.keys
    
    # OpenAI
    read -p "Enter OpenAI API key (or press Enter to skip): " openai_key
    if [ ! -z "$openai_key" ]; then
        echo "SIZECOMPARATOR_OPENAI_API_KEY=$openai_key" >> .env.keys
    fi
    
    # Anthropic
    read -p "Enter Anthropic API key (or press Enter to skip): " anthropic_key
    if [ ! -z "$anthropic_key" ]; then
        echo "SIZECOMPARATOR_ANTHROPIC_API_KEY=$anthropic_key" >> .env.keys
    fi
    
    # X.AI
    read -p "Enter X.AI API key (or press Enter to skip): " xai_key
    if [ ! -z "$xai_key" ]; then
        echo "SIZECOMPARATOR_XAI_API_KEY=$xai_key" >> .env.keys
    fi
    
    # Set permissions
    chmod 600 .env.keys
    echo ""
    echo "Created .env.keys with restricted permissions (600)"
}

# Function to setup main .env file
setup_env_file() {
    if [ ! -f ".env" ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        
        # Ask about prompt profile
        echo ""
        echo "Prompt Profile Selection"
        echo "======================="
        echo "1. verbose    - Detailed, engaging responses"
        echo "2. concise    - Brief, focused responses (default)"
        echo "3. ultra_concise - Minimal one-sentence responses"
        echo ""
        read -p "Select prompt profile (1-3, default=2): " profile_choice
        
        case "$profile_choice" in
            1)
                sed -i 's/SIZECOMPARATOR_PROMPT_PROFILE=concise/SIZECOMPARATOR_PROMPT_PROFILE=verbose/' .env
                echo "Set prompt profile to: verbose"
                ;;
            3)
                sed -i 's/SIZECOMPARATOR_PROMPT_PROFILE=concise/SIZECOMPARATOR_PROMPT_PROFILE=ultra_concise/' .env
                echo "Set prompt profile to: ultra_concise"
                ;;
            *)
                echo "Set prompt profile to: concise (default)"
                ;;
        esac
        
        # Ask about environment
        echo ""
        read -p "Is this for production? (y/N): " is_prod
        if [[ "$is_prod" =~ ^[Yy]$ ]]; then
            sed -i 's/SIZECOMPARATOR_ENV=development/SIZECOMPARATOR_ENV=production/' .env
            sed -i 's/SIZECOMPARATOR_DEBUG=true/SIZECOMPARATOR_DEBUG=false/' .env
            
            # Generate secure secret key
            secret_key=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
            sed -i "s/SIZECOMPARATOR_SECRET_KEY=.*/SIZECOMPARATOR_SECRET_KEY=$secret_key/" .env
            echo "Generated secure secret key for production"
        fi
    else
        echo ".env file already exists"
    fi
}

# Function to verify setup
verify_setup() {
    echo ""
    echo "Verifying setup..."
    echo "=================="
    
    # Check files exist
    [ -f ".env" ] && echo "✓ .env exists" || echo "✗ .env missing"
    [ -f ".env.keys" ] && echo "✓ .env.keys exists" || echo "✗ .env.keys missing"
    
    # Check for at least one API key
    if [ -f ".env.keys" ]; then
        if grep -q "SIZECOMPARATOR_.*_API_KEY=" .env.keys; then
            echo "✓ At least one API key configured"
        else
            echo "✗ No API keys found in .env.keys"
        fi
    fi
    
    # Check prompt profile
    if [ -f ".env" ]; then
        profile=$(grep "SIZECOMPARATOR_PROMPT_PROFILE=" .env | cut -d'=' -f2)
        echo "✓ Prompt profile: $profile"
    fi
    
    echo ""
    echo "Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Review .env for additional configuration"
    echo "2. Start the application with: python run_unified_server.py"
    echo "3. For production deployment, see DEPLOYMENT.md"
}

# Main execution
echo "Weight What? Environment Setup"
echo "=============================="

setup_env_file
prompt_for_keys
verify_setup