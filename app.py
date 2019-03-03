from watson_workspace_sdk import verify_workspace_origin, handle_verification
from watson_workspace_sdk import Message, Client, Annotation, Card
from watson_workspace_sdk.models.webhook import Webhook
from flask import Flask, request
import random
import os
import logging

app = Flask(__name__)

APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
workspace_connection = Client(APP_ID, APP_SECRET)
MESSAGES_WEBHOOK_SECRET = os.environ.get("MESSAGES_WEBHOOK_SECRET")
ANNOTATIONS_WEBHOOK_SECRET = os.environ.get("ANNOTATIONS_WEBHOOK_SECRET")


@app.route('/workspace/messages', methods=["POST"])
@verify_workspace_origin(MESSAGES_WEBHOOK_SECRET)
@handle_verification(MESSAGES_WEBHOOK_SECRET)
def message_webhook():
    webhook_event = Webhook.from_json(request.json)
    if webhook_event.user_id == workspace_connection.id:
        return ""  # ignore messages from this bots
    if request.json.get("content") != "Let's play":
        return ""
    json_payload = request.json
    try:
        workspace_message = Message.create(space_id=json_payload.get("spaceId"),title="Let's play Rock, Paper, Scissors",
                                           text="Which one will you play? \\nRock Paper Scissors", actor="RPS Bot",color="blue")
        workspace_message.add_focus(start=37, end=45, actions='"/RPS Rock"')
        workspace_message.add_focus(start=26, end=30, actions='"/RPS Scissors"')
        workspace_message.add_focus(start=31, end=35, actions='"/RPS Paper"')
    except Exception as e:
        logging.info(f"Hit an exception {e}")
    return ""


@app.route('/workspace/annotations', methods=["POST"])
@verify_workspace_origin(ANNOTATIONS_WEBHOOK_SECRET)
@handle_verification(ANNOTATIONS_WEBHOOK_SECRET)
def annotation_webhook():
    webhook_event = Webhook.from_json(request.json)
    if webhook_event.annotation_type == "actionSelected":  # check is this user initiated or a bot adding annotations
        # Valid action options should be predefined in WW Actions. RPS [Rock|Paper|Scissors]
        action = webhook_event.annotation.get("actionId")
        if "/Cards" == action:  # User ran the slash command without optional params
            deck = []
            card_list = ["Ace", "King", "Queen", "Jack", "Ten", "Nine", "Eight", "Seven", "Six", "Five", "Four",
                         "Three", "Two", "One"]
            for playing_card in card_list:  # make a Watson Workspace Annotation with 12 attachments
                workspace_card = Card(playing_card, "", "Hearts")
                workspace_card.add_button("This one", "/Cards " + playing_card.lower())
                deck.append(workspace_card)

            Message.message_with_attachment(conversation_id=webhook_event.space_id,
                                            target_dialog_id=webhook_event.annotation.get("targetDialogId"),
                                            target_user_id=webhook_event.user_id,
                                            cards=deck)
        if "/RPS" in action:  # Event triggered from action command or through focus annotations
            options = ["Rock", "Scissors", "Paper"]
            bot_roll = random.choice(options)
            if "/RPS" == action:
                response_annotaiton = Annotation("Rock Scissors Paper", "Choose")
                response_annotaiton.add_button("Rock", "/RPS Rock")
                response_annotaiton.add_button("Paper", "/RPS Paper")
                response_annotaiton.add_button("Scissors", "/RPS Scissors")
                Message.message_with_annotation(conversation_id=webhook_event.space_id,
                                                target_dialog_id=webhook_event.annotation.get("targetDialogId"),
                                                target_user_id=webhook_event.user_id, annotation=response_annotaiton)
            elif "/RPS" in action:
                if action[5:] in options:
                    human_roll = action[5:]
                else:
                    response_annotaiton = Annotation("Rock Scissors Paper", "Not a valid play!")
                    Message.message_with_annotation(conversation_id=webhook_event.space_id,
                                                    target_dialog_id=webhook_event.annotation.get("targetDialogId"),
                                                    target_user_id=webhook_event.user_id, annotation=response_annotaiton)
                    return ""  # Not a valid option, sending message to space and will not go further.
                try:
                    winner = "I" if compare(human_roll, bot_roll) else "you"
                    result = f"Looks like {winner} won"
                except KeyError:
                    result = "Looks like it's a draw"
                response_annotaiton = Annotation("Rock Scissors Paper", f"You rolled {human_roll} \\nI rolled Scissors \\n{result}")
                Message.message_with_annotation(conversation_id=webhook_event.space_id,
                                                target_dialog_id=webhook_event.annotation.get("targetDialogId"),
                                                target_user_id=webhook_event.user_id, annotation=response_annotaiton)
    return ""


def compare(player_choice, cpu_choice): # https://codereview.stackexchange.com/questions/172337/rock-paper-scissors-game-in-python
    results = {('Paper', 'Rock'): True,
               ('Paper', 'Scissors'): False,
               ('Rock', 'Paper'): False,
               ('Rock', 'Scissors'): True,
               ('Scissors', 'Paper'): True,
               ('Scissors', 'Rock'): False}
    return results[(player_choice, cpu_choice)]