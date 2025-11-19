import grpc, os
import schedule_pb2_grpc

SCHEDULE_HOST = 'schedule'
SCHEDULE_PORT = int(os.getenv('SCHEDULE_PORT', 3202))
SCHEDULE_GRPC_URL = f"{SCHEDULE_HOST}:{SCHEDULE_PORT}"

def get_schedule_client():
    """
    Crée un client gRPC pour communiquer avec le service Schedule.
    Utilise la configuration pour déterminer l'adresse correcte.
    """
    channel = grpc.insecure_channel(SCHEDULE_GRPC_URL)
    return schedule_pb2_grpc.ScheduleStub(channel)