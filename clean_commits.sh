#!/bin/bash
# Script to remove Claude co-authorship and emojis from git history

echo "Cleaning git commit messages..."

# Use git filter-branch to rewrite commit messages
git filter-branch -f --msg-filter '
    # Remove Claude co-authorship lines
    sed "/Co-Authored-By: Claude <noreply@anthropic.com>/d" |
    # Remove the robot emoji and text
    sed "s/🤖 Generated with Claude Code//g" |
    sed "s/🤖 Generated with \[Claude Code\](https:\/\/claude.ai\/code)//g" |
    # Remove any remaining emojis (comprehensive pattern)
    sed "s/[😀-🙏🌀-🏿☀-⛿✀-➿🚀-🛿🏀-🏿🐀-🙏🌍-🌿🍀-🍿🎀-🏿]//g" |
    # Clean up extra blank lines that might be left
    sed "/^$/N;/^\n$/d"
' --tag-name-filter cat -- --all

echo "Commit messages cleaned!"
echo ""
echo "To verify the changes, run:"
echo "  git log --all --grep='Claude' -i"
echo ""
echo "WARNING: This has rewritten git history!"
echo "You will need to force push with: git push --force-with-lease"