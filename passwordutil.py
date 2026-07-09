#!/usr/bin/python3
import argon2.low_level
import secrets

def rand(length=32):
    return secrets.token_hex(length)

def hash(password,salt):
    return argon2.low_level.hash_secret(secret=password.encode("utf-8"),salt=salt.encode("utf-8"),time_cost=3,memory_cost=65536,parallelism=4,hash_len=32,type=argon2.low_level.Type.ID).decode("utf-8").split("$")[-1]
