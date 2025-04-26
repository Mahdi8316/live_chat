import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message,Room


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = f"room_{self.scope['url_route']['kwargs']['room_name']}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)
        self.close(code)

    async def receive(self, text_data):
        # print("Recieved Data")
        data_json = json.loads(text_data)
        # print(data_json)
        if data_json.get('action') == 'edit':
            event = {"type": "edit_message", "message" : data_json}
        else:
            event = {"type": "send_message", "message" : data_json}
            
        
        # event = {"type": "send_message", "message": data_json}

        await self.channel_layer.group_send(self.room_name, event)

    async def send_message(self, event):
        data = event["message"]
        message = await self.create_message(data=data)

        # response = {"sender": data["sender"], "message": data["message"]}
        response = {
            "action": "new",
            "id": message.id,
            "sender": data["sender"], 
            "message": data["message"],
            "timestamp": message.timestamp.isoformat()
        }
        
        # await self.send(text_data=json.dumps({"message": response}))
        await self.send(text_data=json.dumps(response))
    async def edit_message(self, event):
        data = event["message"]
        success = await self.update_message(data=data)

        if success:
            response = {
                "action": "edit",
                "id": data["message_id"],
                "sender": data["sender"], 
                "new_message": data["new_message"],
                "edited": True
            }
            await self.send(text_data=json.dumps(response))

    @database_sync_to_async
    def create_message(self, data):
        get_room = Room.objects.get(room_name=data["room_name"])

        if not Message.objects.filter(
            message=data["message"], sender=data["sender"]
        ).exists():
            new_message = Message.objects.create(
                room=get_room, message=data["message"], sender=data["sender"]
            )
            return new_message
        return None
    @database_sync_to_async
    def update_message(self, data):
        try:
            message = Message.objects.get(
                id=data["message_id"],
                sender=data["sender"]  # Ensure only sender can edit
            )
            message.message = data["new_message"]
            message.edited = True
            message.save()
            return True
        except Message.DoesNotExist:
            return False