from django.shortcuts import render


def receipes(request):
    if request.method == "POST":
    data = request.POST
    receipes_image = request.FILES.get('receipe_image')
    receipes_name = data.get('receipe_name')
    receipe_description = data.get('receipe_desc')
    print(receipe_description)
    print(receipes_name)
    print(receipes_image)
    return render(request , 'receipes.html')