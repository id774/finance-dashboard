desc 'Run the app'
task :s do
  system "rackup -p 3000 -o 0.0.0.0"
end
