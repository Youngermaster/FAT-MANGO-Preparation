import heapq

def process_downloads(t, p_heap, np_heap, offset_seconds, priority_fraction):
    completed = []
    
    # Calculate download amount per user
    if len(np_heap) == 0:  # Only priority downloads
        download_amount = t / len(p_heap)
    else:  # Mixed downloads
        priority_download_amount = (t * priority_fraction) / len(p_heap)
        non_priority_download_amount = (t * (1 - priority_fraction)) / len(np_heap)
    
    for i in range(len(p_heap)):
        if len(np_heap) == 0:  # Only priority downloads
            remaining_mb = p_heap[i][0] - download_amount
        else:  # Mixed downloads
            remaining_mb = p_heap[i][0] - priority_download_amount
        
        if remaining_mb <= 0:
            offset_seconds += abs(remaining_mb) / t
            completed.append(i)
        else:
            p_heap[i] = (remaining_mb, p_heap[i][1])  # Update heap with remaining size
    
    for i in reversed(completed):
        heapq.heappop(p_heap)
    
    completed = []
    
    for i in range(len(np_heap)):
        if len(p_heap) == 0:  # Only non-priority downloads
            remaining_mb = np_heap[i][0] - download_amount
        else:  # Mixed downloads
            remaining_mb = np_heap[i][0] - non_priority_download_amount
        
        if remaining_mb <= 0:
            offset_seconds += abs(remaining_mb) / t
            completed.append(i)
        else:
            np_heap[i] = (remaining_mb, np_heap[i][1])  # Update heap with remaining size
    
    for i in reversed(completed):
        heapq.heappop(np_heap)
    
    return offset_seconds

output = 0
n, t = map(int, input().split())
p = []
np = []

# Read input and create heaps with tuples (size, index)
for idx in range(n):
    ch, mb = input().split()
    if ch == "P":
        heapq.heappush(p, (int(mb), idx))
    else:
        heapq.heappush(np, (int(mb), idx))

offset_seconds = 0

# Main processing loop
while len(p) > 0 or len(np) > 0:
    if len(p) > 0:
        if len(np) == 0:
            offset_seconds = process_downloads(t, p, [], offset_seconds, 1)
        else:
            offset_seconds = process_downloads(t, p, np, offset_seconds, 0.75)
    
    if len(np) > 0:
        if len(p) == 0:
            offset_seconds = process_downloads(t, np, [], offset_seconds, 1)
        else:
            offset_seconds = process_downloads(t, np, p, offset_seconds, 0.25)
    
    output += 1

print("%.10f" % (output - offset_seconds))