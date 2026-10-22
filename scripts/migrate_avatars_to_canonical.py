#!/usr/bin/env python3
import os
import re
import shutil
import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
AVATARS_DIR = "/home/james/stacklabs/avatars"

def to_snake_case(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'[^\w]', '', s)
    s = re.sub(r'_+', '_', s)
    return s.strip('_')

def sanitize_url_path(url: str) -> str:
    if not url:
        return url
    
    # Standardize to /avatars/
    if url.startswith('/public/avatars/'):
        url = '/avatars/' + url[16:]
        
    if not url.startswith('/avatars/'):
        return url
        
    parts = url.split('/')
    sanitized_parts = ['', 'avatars']
    
    # Process folders and files
    for p in parts[2:]:
        if not p:
            continue
        if '.' in p:
            name, ext = os.path.splitext(p)
            name = to_snake_case(name)
            ext = ext.lower()
            sanitized_parts.append(f"{name}{ext}")
        else:
            sanitized_parts.append(to_snake_case(p))
            
    return '/'.join(sanitized_parts)

def migrate_files():
    print("=== Migrating Files to snake_case ===")
    for root, dirs, files in os.walk(AVATARS_DIR, topdown=False):
        for file in files:
            name, ext = os.path.splitext(file)
            ext = ext.lower()
            clean_name = to_snake_case(name)
            new_file = f"{clean_name}{ext}"
            if new_file != file:
                old_path = os.path.join(root, file)
                new_path = os.path.join(root, new_file)
                print(f"Renaming file: {old_path} -> {new_path}")
                if os.path.exists(new_path):
                    print(f"Warning: Target {new_path} exists. Deleting redundant old file.")
                    try:
                        os.remove(old_path)
                    except Exception as e:
                        print(f"Error removing {old_path}: {e}")
                else:
                    try:
                        os.rename(old_path, new_path)
                    except Exception as e:
                        print(f"Error renaming {old_path} -> {new_path}: {e}")
                        
        for d in dirs:
            clean_d = to_snake_case(d)
            if clean_d != d:
                old_path = os.path.join(root, d)
                new_path = os.path.join(root, clean_d)
                print(f"Renaming directory: {old_path} -> {new_path}")
                if os.path.exists(new_path):
                    print(f"Target directory {new_path} exists. Merging content.")
                    try:
                        for item in os.listdir(old_path):
                            shutil.move(os.path.join(old_path, item), os.path.join(new_path, item))
                        os.rmdir(old_path)
                    except Exception as e:
                        print(f"Error merging directory {old_path} -> {new_path}: {e}")
                else:
                    try:
                        os.rename(old_path, new_path)
                    except Exception as e:
                        print(f"Error renaming directory {old_path} -> {new_path}: {e}")

def migrate_db():
    print("\n=== Migrating Database Records ===")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Update sys_user table
    c.execute("SELECT user_name, avatar_url FROM sys_user WHERE avatar_url IS NOT NULL AND avatar_url != ''")
    sys_users = c.fetchall()
    for username, avatar_url in sys_users:
        new_url = sanitize_url_path(avatar_url)
        if new_url != avatar_url:
            print(f"sys_user: Updating @{username} avatar_url: {avatar_url} -> {new_url}")
            c.execute("UPDATE sys_user SET avatar_url = ? WHERE user_name = ?", (new_url, username))
            
    # 2. Update persona table
    c.execute("SELECT user_name, avatar_url FROM persona WHERE avatar_url IS NOT NULL AND avatar_url != ''")
    personas = c.fetchall()
    for username, avatar_url in personas:
        new_url = sanitize_url_path(avatar_url)
        if new_url != avatar_url:
            print(f"persona: Updating @{username} avatar_url: {avatar_url} -> {new_url}")
            c.execute("UPDATE persona SET avatar_url = ? WHERE user_name = ?", (new_url, username))
            
    conn.commit()
    conn.close()
    print("Database updates committed successfully.")

if __name__ == "__main__":
    migrate_files()
    migrate_db()
    print("=== Migration Completed ===")
