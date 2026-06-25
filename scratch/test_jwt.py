import asyncio
from datetime import datetime, timedelta
from app.api.auth import create_access_token
from jose import jwt
import time

def main():
    token = create_access_token(data={"sub": "test_user_id"})
    print("Token:", token)
    
    # Decode it and check payload
    payload = jwt.decode(token, "your-secret-key-change-me", algorithms=["HS256"])
    print("Payload:", payload)
    
    current_time = time.time()
    exp_time = payload.get("exp")
    print(f"Current Time (epoch): {current_time}")
    print(f"Exp Time (epoch):     {exp_time}")
    print(f"Difference (hours):   {(exp_time - current_time) / 3600:.2f}")

if __name__ == "__main__":
    main()
