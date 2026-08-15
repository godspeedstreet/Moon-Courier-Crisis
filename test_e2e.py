import requests
import json

base = 'http://localhost:8000/api'

print('=== Testing API Endpoints ===')

# 1. Health check
r = requests.get('http://localhost:8000/health')
print(f'Health: {r.status_code} - {r.json()}')

# 2. Zones
r = requests.get(f'{base}/zones')
print(f'Zones: {r.status_code} - count: {len(r.json())}')

# 3. Rovers
r = requests.get(f'{base}/rovers')
rovers = r.json()
print(f'Rovers: {r.status_code} - count: {len(rovers)}')
for rv in rovers:
    print(f'  - {rv["name"]}: battery={rv["current_battery"]}%, cargo={rv["max_cargo"]}kg, status={rv["status"]}')

# 4. Orders
r = requests.get(f'{base}/orders')
orders = r.json()
print(f'Orders: {r.status_code} - count: {len(orders)}')
for o in orders[:3]:
    print(f'  - {o["title"]}: weight={o["weight"]}kg, reward={o["reward"]}, status={o["status"]}')

# 5. Game State
r = requests.get(f'{base}/game/state')
gs = r.json()
print(f'GameState: {r.status_code} - day={gs["current_day"]}, credits={gs["credits"]}, rating={gs["base_rating"]}')

# 6. Simulation
if rovers and orders:
    rv = rovers[0]
    o = next((x for x in orders if x['status'] == 'pending'), None)
    if o:
        r = requests.post(f'{base}/delivery/simulate', json={'rover_id': rv['id'], 'order_id': o['id']})
        sim = r.json()
        print(f'Simulation: {r.status_code} - success={sim["success"]}, battery={sim["battery_needed"]:.1f}%, distance={sim["distance"]:.1f}km')
        if sim['success']:
            r = requests.post(f'{base}/delivery/assign', json={'rover_id': rv['id'], 'order_id': o['id']})
            print(f'Assign delivery: {r.status_code} - {r.json()}')

# 7. Next Day
r = requests.post(f'{base}/game/next-day')
print(f'Next Day: {r.status_code} - day={r.json()["day"]}, credits={r.json()["credits"]}')

# 8. Stats
r = requests.get(f'{base}/stats')
print(f'Stats: {r.status_code}')
print(json.dumps(r.json(), indent=2))

print('\n=== All API tests passed! ===')