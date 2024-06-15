output = 0
# ! First Case
n = 5
t = 40
p = [10, 20, 200]
np = [100, 300]

# * Uncomment the following cases to test the code
# # ! Second Case
# n = 1
# t = 1
# p = []
# np = [64]

# # ! Third Case
# n = 1
# t = 113
# p = [355]
# np = []

offset_seconds = 0
while len(p) > 0 or len(np) > 0:
  print("Output: ", output)
  print("Priority queue: ", p)
  print("Non-priority queue: ", np)
  pi_to_remove = []
  npi_to_remove = []
  for i in range(len(p)):
    if len(np) == 0:
      p[i] -= t / len(p)
    else:
      # Priority download
      dp = (t * 0.75) / len(p)
      print("Priority download: ", dp)
      p[i] -= dp
    if p[i] <= 0:
      pi_to_remove.append(i)
      if p[i] < 0:
        offset_seconds += abs(p[i]/t)
        print("Offset seconds: ", offset_seconds)
  for i in range(len(np)):
    if len(p) == 0:
      np[i] -= t / len(np)
    else:
      # Non-priority download
      ndp = (t * 0.25) / len(np)
      print("Non-priority download: ", ndp)
      np[i] -= ndp
    if np[i] <= 0:
      npi_to_remove.append(i)
      if np[i] < 0:
        offset_seconds += abs(np[i]/t)
        print("Offset seconds: ", offset_seconds)
  for i in pi_to_remove:
    p.pop(i)
  for i in npi_to_remove:
    np.pop(i)
  output += 1
  
print(offset_seconds)
print(output-offset_seconds)
