"""
🌙 Moon Dev's OpenAI O3-mini Test Script
Built with love by Moon Dev 🚀
"""

from openai import OpenAI
from termcolor import cprint
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

def test_o3_mini():
    """Test the OpenAI O3-mini model with a fun coding challenge"""
    
    # Initialize client with correct env variable name
    cprint("🚀 Moon Dev's O3-mini test launching...", "cyan")
    api_key = os.getenv('OPENAI_KEY')  # Changed to match your .env setup
    if not api_key:
        cprint("❌ No OpenAI API key found! Make sure OPENAI_KEY is set in your .env file", "red")
        return
        
    client = OpenAI(api_key=api_key)
    
    # Test prompt
    prompt = """
    Write a Python function that takes a list of numbers and returns the 
    sum of all even numbers in the list. Include detailed comments.
    """
    
    cprint("🤔 Moon Dev is thinking deep thoughts...", "yellow")
    try:
        response = client.chat.completions.create(
            model="o3-mini",
            reasoning_effort="medium",  # Balanced reasoning mode
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        cprint("✨ Moon Dev's O3-mini model responded successfully!", "green")
        print("\n🎯 Generated Response:")
        print(response.choices[0].message.content)
        
    except Exception as e:
        cprint(f"❌ Oops! Even Moon Dev hits bumps sometimes: {str(e)}", "red")

if __name__ == "__main__":
    cprint("🌙 Moon Dev AI Lab - O3-mini Test", "magenta")
    test_o3_mini()
