output = 0
n, t = map(int, input().split())
p = []
np = []
for _ in range(n):
    ch, mb = input().split()
    if ch == "P":
        p.append(int(mb))
    else:
        np.append(int(mb))

offset_seconds = 0
while len(p) > 0 or len(np) > 0:
    pi_to_remove = []
    npi_to_remove = []
    for i in range(len(p)):
        if p[i] == 0:
            pi_to_remove.append(i)
            continue
        if len(np) == 0:
            p[i] -= t / len(p)
        else:
            # Priority download
            dp = (t * 0.75) / len(p)
            p[i] -= dp
        if p[i] <= 0:
            pi_to_remove.append(i)
            if p[i] < 0:
                offset_seconds += abs(p[i] / t)
    for i in range(len(np)):
        if np[i] == 0:
            npi_to_remove.append(i)
            continue
        if len(p) == 0:
            np[i] -= t / len(np)
        else:
            # Non-priority download
            ndp = (t * 0.25) / len(np)
            np[i] -= ndp
        if np[i] <= 0:
            npi_to_remove.append(i)
            if np[i] < 0:
                offset_seconds += abs(np[i] / t)

    p = [item for idx, item in enumerate(p) if idx not in pi_to_remove]
    np = [item for idx, item in enumerate(np) if idx not in npi_to_remove]
    output += 1

print("%.10f" % (output - offset_seconds))