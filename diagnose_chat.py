"""Check configured Gemini access without printing API keys or student information."""
from configuration import chat_config
from agent import DECLARATIONS, SYSTEM, provider_error

def main():
    key,model,error=chat_config()
    if error:
        print(error)
        return 1
    print('Secrets syntax: valid; API key: configured; model:',model)
    try:
        from google import genai
        from google.genai import types
        client=genai.Client(api_key=key,http_options={'timeout':30000})
        response=client.models.generate_content(model=model,
            contents='Find Python backend internships. Call search_jobs.',
            config=types.GenerateContentConfig(system_instruction=SYSTEM,
                tools=[types.Tool(function_declarations=DECLARATIONS)],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)))
        calls=list(response.function_calls or [])
        print('Gemini response: received; requested tools:',[call.name for call in calls])
        return 0
    except Exception as error:
        print('Gemini status:',getattr(error,'code',None) or type(error).__name__)
        print(provider_error(error))
        return 1

if __name__=='__main__':
    raise SystemExit(main())
