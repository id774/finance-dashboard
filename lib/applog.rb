class AppLog
  def initialize(app, logger)
    @app, @logger = app, logger
  end

  def call(env)
    env["app.logger"] = @logger
    @app.call(env)
  end
end
