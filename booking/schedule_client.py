import grpc, os
import schedule_pb2_grpc
import config

def get_schedule_client():
    """
    Crée un client gRPC pour communiquer avec le service Schedule.
    Utilise la configuration pour déterminer l'adresse correcte.
    """
    channel = grpc.insecure_channel(config.SCHEDULE_GRPC_URL)
    return schedule_pb2_grpc.ScheduleStub(channel)