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

while len(p) > 0 or len(np) > 0:
  print("Output: ", output)
  print("Priority queue: ", p)
  print("Non-priority queue: ", np)
  for i in range(len(p)):
    if len(np) == 0:
      p[i] -= t
    else:
      # Priority download
      dp = (t * 0.75) / len(p)
      print("Priority download: ", dp)
      p[i] -= dp
    if p[i] <= 0:
      p.pop(i)
      break
  for i in range(len(np)):
    if len(p) == 0:
      np[i] -= t
    else:
      # Non-priority download
      ndp = (t * 0.25) / len(np)
      print("Non-priority download: ", ndp)
      np[i] -= ndp
    if np[i] <= 0:
      np.pop(i)
      break
  output += 1
  

print(output)
