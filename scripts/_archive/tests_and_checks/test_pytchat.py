import pytchat
chat = pytchat.create(video_id="NKJIEkPzj3w")
for i in range(5):
    if chat.is_alive():
        for c in chat.get().sync_items():
            print(f"{c.datetime} [{c.author.name}]- {c.message}")
            break
